import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter, MaxNLocator
from matplotlib.patches import Patch

# Page configuration
st.set_page_config(page_title="iRacing Stint Strategy & Telemetry", layout="wide", page_icon="🏎️")

st.title("🏎️ iRacing Stint Strategy & Lap Telemetry Plotter")
st.write("Upload your raw iRacing Lap Chart JSON file below to generate a comprehensive, interactive telemetry dashboard for your team.")
st.write("How to download JSON file: iRacing console->Results & Stats->Results->Lap Chart tab->Download Lap Data")

# 1. Interactive File Uploader
uploaded_file = st.file_uploader("Step 1: Drag and drop your raw iRacing JSON file here", type=["json"])

if uploaded_file is not None:
    # Parse raw JSON
    raw_data = json.load(uploaded_file)
    
    # Extract available team names dynamically
    all_teams = set()
    for item in raw_data.get("lapData", []):
        for key, val in item.items():
            if key.startswith("lap_") and val.get("name"):
                all_teams.add(val.get("name"))
                
    sorted_teams = sorted(list(all_teams))
    
    # 2. Interactive Team Selection
    st.success("File uploaded successfully!")
    team_name = st.selectbox("Step 2: Select your Team Name from the list", options=sorted_teams)
    
    if team_name:
        st.info(f"Processing telemetry for '{team_name}'...")
        
        # 3. Parse and Clean Dataset
        all_team_laps = []
        for idx, item in enumerate(raw_data.get("lapData", [])):
            for key, val in item.items():
                if key.startswith("lap_") and val.get("name") == team_name:
                    all_team_laps.append({
                        "lap_number": val.get("lap_number"),
                        "driver": val.get("display_name"),
                        "lap_time": val.get("lap_time") / 10000.0 if val.get("lap_time") and val.get("lap_time") > 0 else None,
                        "is_pit": "pitted" in val.get("lap_events", []),
                        "incident": val.get("incident", False),
                        "lap_position": val.get("lap_position")
                    })

        df = pd.DataFrame(all_team_laps).sort_values("lap_number").reset_index(drop=True)
        df = df[df['lap_number'] > 0].reset_index(drop=True)  # strip pre-grid lap 0

        df_cleaned = df[df['lap_time'] > 0].copy()
        df_filtered = df_cleaned[~df_cleaned['is_pit']].copy()
        df_filtered['driver_clean'] = df_filtered['driver'].str.rstrip('0123456789 ')

        # Setup Colors
        unique_drivers = sorted(df_filtered['driver_clean'].unique())
        default_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        colors = {driver: default_palette[i % len(default_palette)] for i, driver in enumerate(unique_drivers)}

        def to_min_sec(x, pos):
            return f"{int(x // 60)}:{x % 60:06.3f}"

        sns.set_theme(style="whitegrid")

        # Create interactive tabs to keep the UI clean and professional
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Chronological Scatter", 
            "📊 Ranked Pace Curves", 
            "📉 Lap Distribution", 
            "⚡ Advanced Insights", 
            "⛽ Stint Strategy"
        ])

        # --- TAB 1: Chronological Scatter ---
        with tab1:
            st.subheader("Chronological Lap Times (Pits Filtered)")
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.scatterplot(
                data=df_filtered, 
                x='lap_number', 
                y='lap_time', 
                hue='driver_clean', 
                palette=colors, 
                hue_order=unique_drivers,
                s=40, 
                alpha=0.8, 
                edgecolor='none',
                ax=ax
            )
            ax.set_xlabel('Race Lap Number')
            ax.set_ylabel('Lap Time (MM:SS.fff)')
            ax.yaxis.set_major_formatter(FuncFormatter(to_min_sec))
            ax.legend(title="Drivers", frameon=True)
            st.pyplot(fig)

        # --- TAB 2: Ranked Pace ---
        with tab2:
            st.subheader("Ranked Pace Profiles")
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            df_filtered['driver_lap_rank'] = df_filtered.groupby('driver_clean')['lap_time'].rank(method='first').astype(int)

            for driver in unique_drivers:
                driver_data = df_filtered[df_filtered['driver_clean'] == driver].sort_values('lap_time')
                axes[0].scatter(driver_data['driver_lap_rank'], driver_data['lap_time'], color=colors[driver], label=driver, s=20, alpha=0.7)
                axes[0].plot(driver_data['driver_lap_rank'], driver_data['lap_time'], color=colors[driver], alpha=0.25)

            axes[0].set_title('Pace Ranking Comparison (Fastest to Slowest)', fontweight='bold')
            axes[0].set_xlabel('Total Laps Completed (Ranked)')
            axes[0].set_ylabel('Lap Time (MM:SS.fff)')
            axes[0].yaxis.set_major_formatter(FuncFormatter(to_min_sec))
            axes[0].legend(title="Drivers")

            df_sorted_team = df_filtered.sort_values('lap_time').reset_index(drop=True)
            df_sorted_team['team_lap_rank'] = df_sorted_team.index + 1
            sns.scatterplot(
                data=df_sorted_team, 
                x='team_lap_rank', 
                y='lap_time', 
                hue='driver_clean', 
                palette=colors, 
                hue_order=unique_drivers,
                s=30, 
                alpha=0.8, 
                edgecolor='none', 
                ax=axes[1]
            )
            axes[1].set_title('Team Overall Pace Curve', fontweight='bold')
            axes[1].set_xlabel('Total Laps (Team Rank)')
            axes[1].set_ylabel('Lap Time (MM:SS.fff)')
            axes[1].yaxis.set_major_formatter(FuncFormatter(to_min_sec))
            axes[1].legend(title="Drivers")
            st.pyplot(fig)

        # --- TAB 3: Lap Histogram ---
        with tab3:
            st.subheader("Lap Time Distribution Comparison")
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.histplot(
                data=df_filtered, 
                x='lap_time', 
                hue='driver_clean', 
                palette=colors, 
                hue_order=unique_drivers,
                element='step', 
                stat='count', 
                common_norm=False, 
                kde=True, 
                alpha=0.15, 
                bins=60,
                ax=ax
            )
            ax.set_xlabel('Lap Time (MM:SS.fff)')
            ax.set_ylabel('Number of Laps')
            ax.xaxis.set_major_formatter(FuncFormatter(to_min_sec))
            st.pyplot(fig)

        # --- TAB 4: Advanced Insights ---
        with tab4:
            st.subheader("Pace Evolution vs. Incident Steps & Position")
            fig, axes = plt.subplots(1, 2, figsize=(18, 7))

            for driver, group in df_filtered.groupby('driver_clean'):
                group = group.sort_values('lap_number')
                group['chunk'] = (group['lap_number'].diff() > 5).cumsum()
                for chunk_id, chunk in group.groupby('chunk'):
                    chunk = chunk.copy()
                    chunk['rolling_pace'] = chunk['lap_time'].rolling(window=3, min_periods=1).mean()
                    axes[0].plot(chunk['lap_number'], chunk['rolling_pace'], color=colors[driver], linewidth=2.5, alpha=0.85)
                    axes[0].scatter(chunk['lap_number'], chunk['lap_time'], color=colors[driver], s=15, alpha=0.15)

            for driver in unique_drivers:
                axes[0].plot([], [], color=colors[driver], label=driver, linewidth=3)
            axes[0].set_title('Race Pace Evolution (3-Lap Rolling Average)', fontweight='bold')
            axes[0].set_xlabel('Race Lap Number')
            axes[0].set_ylabel('Lap Time (MM:SS.fff)')
            axes[0].yaxis.set_major_formatter(FuncFormatter(to_min_sec))
            axes[0].legend(title="Drivers", frameon=True)
            axes[0].set_ylim(df_filtered['lap_time'].min() - 0.5, 150)

            df_cleaned['driver_clean'] = df_cleaned['driver'].str.rstrip('0123456789 ')
            df_cleaned['cum_incidents'] = df_cleaned['incident'].astype(int).cumsum()
            df_cleaned['chunk'] = (df_cleaned['driver_clean'] != df_cleaned['driver_clean'].shift()).cumsum()

            axes[1].plot(df_cleaned['lap_number'], df_cleaned['cum_incidents'], color='#7f7f7f', linewidth=2, linestyle='--', alpha=0.5)
            for chunk_id, chunk in df_cleaned.groupby('chunk'):
                driver = chunk['driver_clean'].iloc[0]
                if pd.isna(driver): continue
                axes[1].plot(chunk['lap_number'], chunk['cum_incidents'], color=colors[driver], linewidth=3.5)
                incidents_in_chunk = chunk[chunk['incident'] == True]
                if not incidents_in_chunk.empty:
                    axes[1].scatter(incidents_in_chunk['lap_number'], incidents_in_chunk['cum_incidents'], color='black', edgecolor='white', marker='X', s=60, zorder=5)

            df_sorted = df.sort_values('lap_number')
            position_color = '#9467bd'
            axes[1].plot(df_sorted['lap_number'], df_sorted['lap_position'], color=position_color, linewidth=2.0, alpha=0.8)

            axes[1].set_title('Team Incident Tracker & Race Position', fontweight='bold')
            axes[1].set_xlabel('Race Lap Number')
            axes[1].set_ylabel('Total Incidents / Race Position', fontweight='bold')
            axes[1].yaxis.set_major_locator(MaxNLocator(integer=True))

            legend_elements = [Patch(facecolor=colors[d], edgecolor=colors[d], label=d) for d in unique_drivers]
            legend_elements.append(plt.Line2D([0], [0], marker='X', color='w', markerfacecolor='black', markersize=10, label='Incident Event'))
            legend_elements.append(plt.Line2D([0], [0], color=position_color, linewidth=2.0, label='Race Position'))
            axes[1].legend(handles=legend_elements, title="Stints, Events & Position", bbox_to_anchor=(0.18, 0.96), loc='upper left', frameon=True)
            st.pyplot(fig)

        # --- TAB 5: Stint Performance ---
        with tab5:
            st.subheader("Stint Analysis (Fuel Windows & Clean Pace)")
            df_team = df.copy()
            df_team['flying_block'] = (df_team['is_pit'] == True).cumsum()
            flying_groups = df_team[df_team['is_pit'] == False]

            stints_list = []
            stint_number = 1
            for b_id, group in flying_groups.groupby('flying_block'):
                driver = group['driver'].iloc[0].rstrip('0123456789 ')
                
                start_lap = group['lap_number'].min()
                end_lap = group['lap_number'].max()
                avg_pace = group['lap_time'].mean()
                
                actual_start = start_lap - 1 if (start_lap - 1 in df_team['lap_number'].values and df_team[df_team['lap_number'] == start_lap - 1]['is_pit'].values[0]) else start_lap
                actual_end = end_lap + 1 if (end_lap + 1 in df_team['lap_number'].values and df_team[df_team['lap_number'] == end_lap + 1]['is_pit'].values[0]) else end_lap
                total_stint_laps = actual_end - actual_start + 1
                
                stints_list.append({
                    "stint_number": stint_number,
                    "driver": driver,
                    "total_laps": total_stint_laps,
                    "avg_pace": avg_pace
                })
                stint_number += 1
            df_stints_final = pd.DataFrame(stints_list)

            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            for driver in unique_drivers:
                group = df_stints_final[df_stints_final['driver'] == driver]
                axes[0].scatter(group['stint_number'], group['total_laps'], color=colors[driver], label=driver, s=100, edgecolors='k', zorder=3)
            axes[0].plot(df_stints_final['stint_number'], df_stints_final['total_laps'], color='#7f7f7f', linestyle='-', linewidth=1.5, alpha=0.5, zorder=1)
            axes[0].set_title('Stint Length (Laps per Pit Stop)', fontweight='bold')
            axes[0].set_xlabel('Stint Sequence Number')
            axes[0].set_ylabel('Total Laps Completed')
            axes[0].set_ylim(0, 30)
            axes[0].legend(title="Drivers", frameon=True)

            for driver in unique_drivers:
                group = df_stints_final[df_stints_final['driver'] == driver]
                axes[1].scatter(group['stint_number'], group['avg_pace'], color=colors[driver], label=driver, s=100, edgecolors='k', zorder=3)
            axes[1].plot(df_stints_final['stint_number'], df_stints_final['avg_pace'], color='#7f7f7f', linestyle='-', linewidth=1.5, alpha=0.5, zorder=1)
            axes[1].set_title('Average Clean Pace per Stint', fontweight='bold')
            axes[1].set_xlabel('Stint Sequence Number')
            axes[1].set_ylabel('Average Lap Time (MM:SS.fff)')
            axes[1].yaxis.set_major_formatter(FuncFormatter(to_min_sec))
            axes[1].legend(title="Drivers", frameon=True)
            st.pyplot(fig)
