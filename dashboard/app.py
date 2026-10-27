
from pathlib import Path
import sys
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import tempfile 

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.baseline_learning import (
    create_baseline,
    LIVE_DATA_PATH,
    WINDOW_SIZE,
)
from src.baseline_registry import (
    review_baseline,
    activate_baseline,
    get_active_baseline,
)
from src.baseline_monitor import monitor_machine


def render_prediction_overview(prediction_df):
    """Render prediction metrics, machine status, and anomaly scores."""
    total_windows = len(prediction_df)
    normal_windows = (prediction_df["prediction"] == "Normal").sum()
    unusual_windows = (prediction_df["prediction"] == "Unusual").sum()

    col1, col2, col3 = st.columns(3)

    col1.metric("Windows Analysed", total_windows)
    col2.metric("Normal Windows", normal_windows)
    col3.metric("Unusual Windows", unusual_windows)

    st.subheader("Machine Status")

    if unusual_windows > 0:
        st.warning(
            f"{unusual_windows} unusual vibration windows detected. "
            "Inspect the highlighted periods."
        )
    else:
        st.success("No unusual vibration patterns detected.")

    st.subheader("Anomaly Score Over Time")

    fig = px.scatter(
        prediction_df,
        x="start_time",
        y="anomaly_score",
        color="prediction",
        color_discrete_map={
            "Normal": "#16a34a",
            "Unusual": "#dc2626",
        },
        hover_data=["end_time", "scenario"],
        labels={
            "start_time": "Time (seconds)",
            "anomaly_score": "Anomaly Score",
            "prediction": "Model Prediction",
        },
        title="Lower scores indicate more anomalous patterns",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_prediction_table(prediction_df):
    """Render the filterable prediction details table."""
    st.subheader("Prediction Details")

    filter_choice = st.selectbox(
        "Filter by prediction",
        ["All", "Normal", "Unusual"],
    )

    if filter_choice == "All":
        filtered_df = prediction_df
    else:
        filtered_df = prediction_df[
            prediction_df["prediction"] == filter_choice
        ]

    st.dataframe(
        filtered_df[
            [
                "start_time",
                "end_time",
                "prediction",
                "anomaly_score",
                "scenario",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# 1. Configure the dashboard
st.set_page_config(
    page_title="AI-IoT Predictive Maintenance",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ AI-IoT Predictive Maintenance")
st.caption("Live motor vibration monitoring and anomaly detection")

# Live sensor is the only dashboard mode.
data_source = "Live Sensor"
st.sidebar.header("Live Monitoring")
st.sidebar.text_input(
    "Machine ID",
    value="MOTOR_001",
    disabled=True,
)



# Healthy baseline learning and live anomaly monitoring
MACHINE_ID = "MOTOR_001"
RAW_DATA_PATH = LIVE_DATA_PATH

st.subheader("Healthy Baseline Learning")
st.write(
    "Record at least 30 seconds of sensor data while the motor "
    "is running in verified healthy condition."
)

healthy_confirmed = st.checkbox(
    "I confirm the motor is running in a verified healthy condition.",
    key="healthy_confirmed",
)

sensor_configuration = st.text_input(
    "Sensor configuration",
    value="MPU6050; 100 Hz; mounted securely on motor",
    key="sensor_configuration",
)

if st.button("Start 30-second healthy learning"):
    if not healthy_confirmed:
        st.error("Confirm healthy motor operation first.")
    elif not RAW_DATA_PATH.exists():
        st.error("Live sensor CSV not found. Start the serial collector first.")
    else:
        raw = pd.read_csv(RAW_DATA_PATH)
        st.session_state["learning_start_rows"] = len(raw)
        st.session_state["learning_start_time"] = time.time()
        st.session_state["learning_started"] = True
        st.session_state["baseline_ready"] = False
        st.session_state["pending_baseline_path"] = None
        st.success("Recording started. Keep the collector and motor running.")



if st.session_state.get("learning_started", False):

    @st.fragment(run_every="1s")
    def healthy_learning_progress():
        if not st.session_state.get("learning_started", False):
            return

        elapsed = time.time() - st.session_state["learning_start_time"]
        st.progress(min(elapsed / 30.0, 1.0))
        st.write(f"Recording progress: {min(elapsed, 30):.0f}/30 seconds")

        if elapsed < 30:
            return

        st.session_state["learning_started"] = False

        if not healthy_confirmed:
            st.error("Confirm healthy motor operation before creating a baseline.")
            return

        if not RAW_DATA_PATH.exists():
            st.error("Live sensor CSV was not found.")
            return

        try:
            
            raw = pd.read_csv(RAW_DATA_PATH)
            start_rows = st.session_state["learning_start_rows"]

            # Use only readings appended during the learning period.
            new_rows = raw.iloc[start_rows:].copy()

            # Prevent readings received after the 30-second deadline
            # from entering the healthy baseline.
            learning_start_time = st.session_state["learning_start_time"]
            learning_end_time = learning_start_time + 30.0

            new_rows = new_rows[
                (new_rows["received_timestamp"] >= learning_start_time)
                & (new_rows["received_timestamp"] <= learning_end_time)
            ].copy()


            if len(new_rows) < 2000:
                st.error(
                    f"Only {len(new_rows)} new readings were collected. "
                    "At least 2000 readings are required."
                )
                return

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_csv = Path(temp_dir) / "healthy_recording.csv"
                new_rows.to_csv(temp_csv, index=False)

                baseline_path = create_baseline(
                    machine_id=MACHINE_ID,
                    sensor_configuration=sensor_configuration,
                    healthy_operation_verified=True,
                    csv_path=temp_csv,
                    minimum_windows=20,
                )

            st.session_state["pending_baseline_path"] = str(baseline_path)
            st.session_state["baseline_ready"] = True
            st.success(f"Baseline created for review: {baseline_path.name}")
            st.info("The baseline is not active yet. Review and activate it below.")

        except Exception as error:
            st.error(f"Baseline creation failed: {error}")

    healthy_learning_progress()




st.subheader("Review and Activate Baseline")

# Find saved baselines even if Streamlit session state was lost.
baseline_dir = PROJECT_ROOT / "data" / "baselines" / MACHINE_ID
baseline_files = sorted(baseline_dir.glob("baseline_v*.json"))

if not baseline_files:
    st.info("No saved baseline files were found. Record healthy data first.")
else:
    baseline_names = [path.name for path in baseline_files]

    # Prefer the baseline created during the current session, if available.
    pending_path = st.session_state.get("pending_baseline_path")
    default_index = 0

    if pending_path:
        pending_name = Path(pending_path).name
        if pending_name in baseline_names:
            default_index = baseline_names.index(pending_name)

    selected_name = st.selectbox(
        "Select a saved baseline",
        baseline_names,
        index=default_index,
    )

    selected_path = baseline_dir / selected_name
    version_text = selected_path.stem.replace("baseline_v", "")

    if version_text.isdigit():
        baseline_version = int(version_text)

        if st.button("Review and activate selected baseline"):
            if not healthy_confirmed:
                st.error(
                    "Confirm that the recorded motor was operating healthily."
                )
            else:
                try:
                    review = review_baseline(MACHINE_ID, baseline_version)
                    st.write("Baseline review results")
                    st.json(review)

                    activate_baseline(
                        machine_id=MACHINE_ID,
                        version=baseline_version,
                        approved_by="Project operator",
                        approval_note=(
                            "Reviewed healthy motor reference recording."
                        ),
                        confirmed_healthy=True,
                    )

                    st.session_state["pending_baseline_path"] = None
                    st.success(
                        f"Baseline {selected_name} activated successfully."
                    )
                    st.rerun()

                except Exception as error:
                    st.error(f"Review or activation failed: {error}")



st.divider()
st.subheader("Live Anomaly Monitoring")


@st.fragment(run_every="1s")
def live_anomaly_panel():
    try:
        prediction_df = monitor_machine(
            MACHINE_ID,
            csv_path=RAW_DATA_PATH,
            persistence_window=5,
            required_anomalies=3,
        )
    except (FileNotFoundError, ValueError, KeyError, OSError) as error:
        st.info(f"Live monitoring is waiting: {error}")
        return

    if prediction_df.empty:
        st.info(
            "Baseline is active. Waiting for enough new readings "
            "to form the first complete 100-reading window."
        )
        return

    latest = prediction_df.iloc[-1]
    persistent_fault = bool(latest["persistent_fault"])
    recent_anomalies = int(latest["recent_anomalies"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Windows Analysed", len(prediction_df))
    col2.metric("Recent Anomalous Windows", f"{recent_anomalies}/5")
    col3.metric("Active Baseline", str(latest["baseline_version"]))

    if persistent_fault:
        st.error(
            "POSSIBLE FAULT DETECTED — recurring unusual vibration. "
            "Inspect the machine."
        )
    elif bool(latest["baseline_deviation"]):
        st.warning(
            "Unusual vibration detected in the latest window. "
            "Monitoring for recurrence."
        )
    else:
        st.success(
            "Machine vibration is within the learned healthy range."
        )

    chart_df = prediction_df.copy()
    chart_df["prediction"] = chart_df["baseline_deviation"].map(
        {True: "Unusual", False: "Normal"}
    )
    chart_df["anomaly_score"] = chart_df["deviating_feature_count"]

    st.subheader("Live Anomaly Score Over Time")

    
    chart_df["window_time"] = pd.to_datetime(
        chart_df["window_received_timestamp"],
        unit="s",
        utc=True,
    ).dt.tz_convert("Asia/Kolkata")

    fig = px.scatter(
        chart_df.tail(60),
        x="window_time",
        y="anomaly_score",
        color="prediction",
        color_discrete_map={
            "Normal": "#16a34a",
            "Unusual": "#dc2626",
        },
        labels={
            "window_time": "Window received at (IST)",
            "anomaly_score": "Number of deviating features",
            "prediction": "Window result",
        },
        title="Live Anomaly Score Over Time",
    )
    st.plotly_chart(fig, use_container_width=True)


    st.subheader("Recent Monitoring Windows")
    st.dataframe(
        chart_df.tail(10)[
            [
                "start_time",
                "end_time",
                "deviating_feature_count",
                "deviating_features",
                "recent_anomalies",
                "persistent_fault",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


live_anomaly_panel()


# 6. Plot the original vibration signals
st.subheader("Vibration Signal Monitoring")

if data_source == "Live Sensor":
    RAW_DATA_PATH = (
        PROJECT_ROOT / "data" / "processed" / "live_sensor_data.csv"
    )

    @st.fragment(run_every="1s")
    def live_vibration_chart():
        if not RAW_DATA_PATH.exists():
            st.error(f"Live sensor data file not found: {RAW_DATA_PATH}")
            return

        try:
            raw_df = pd.read_csv(RAW_DATA_PATH)
        except (OSError, pd.errors.ParserError) as error:
            st.warning(f"Could not read live sensor data: {error}")
            return

        required_columns = ["time_seconds", "ax_g", "ay_g", "az_g"]
        if not set(required_columns).issubset(raw_df.columns):
            st.error("Live CSV is missing required columns.")
            return

        if raw_df.empty:
            st.info("Waiting for sensor readings...")
            return

        axis_choice = st.multiselect(
            "Select vibration axes",
            options=["ax_g", "ay_g", "az_g"],
            default=["ax_g", "ay_g", "az_g"],
            key="live_axis_choice",
        )

        if not axis_choice:
            st.info("Select at least one vibration axis.")
            return

        # Show the latest 10 seconds of data.
        latest_time = raw_df["time_seconds"].max()
        visible_df = raw_df[
            raw_df["time_seconds"] >= latest_time - 10
        ].copy()

        signal_long_df = visible_df[
            ["time_seconds", *axis_choice]
        ].melt(
            id_vars="time_seconds",
            var_name="Axis",
            value_name="Acceleration (g)",
        )

        signal_fig = px.line(
            signal_long_df,
            x="time_seconds",
            y="Acceleration (g)",
            color="Axis",
            title="Live Vibration — Latest 10 Seconds",
            labels={
                "time_seconds": "Time (seconds)",
                "Acceleration (g)": "Acceleration (g)",
            },
        )

        # Zero is a reference, not a fault threshold.
        signal_fig.add_hline(
            y=0,
            line_dash="dash",
            annotation_text="Zero reference",
        )

        st.plotly_chart(
            signal_fig,
            use_container_width=True,
        )

        st.caption(
            f"Latest sensor timestamp: {latest_time:.2f} seconds"
        )

    live_vibration_chart()


st.caption(
    "Live sensor monitoring prototype. "
    "An anomaly alert indicates unusual vibration, not a confirmed machine fault."
)