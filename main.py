# from zoneinfo import ZoneInfo
import os 
import pandas as pd
import logging
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import logging
import os
import webbrowser
from pathlib import Path

OUTPUT_DIR = "output"
INPUT_DIR = "input"
# UTC_TZ = ZoneInfo('UTC')
# MOSCOW_TZ = ZoneInfo('Europe/Moscow')
HISTORY_HTML = os.path.join(OUTPUT_DIR, "macro.html")
AVERAGED_HTML = os.path.join(OUTPUT_DIR, "averaged.html")
PLOTLY_COMBINED_HTML = os.path.join(OUTPUT_DIR, "index.html")

# Create necessary directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)

COMMON_MARGIN = dict(l=25, r=25, t=50, b=50)
CONFIG = {
    'displaylogo': False,
    'responsive': True,
    'modeBarButtonsToRemove': [ 'lasso2d' ]
}

def get_info_total(dataset):
    num_of_datapoints = len(dataset)
    start_time = dataset['datetime'].min()
    end_time = dataset['datetime'].max()
    t1 = f"Первая точка данных:    {start_time}\n"
    t2 = f"Последняя точка данных: {end_time}\n"
    t3 = f"Количество точек данных: {num_of_datapoints}\n" 
    t4 = f"Первые точки:\n{dataset.head()}\n ... "
    text_for_legend = t1 + t2 + t3 + t4 
    return text_for_legend

def prepare_dataset(pathname):
    print(f"\nЧитаю файл: {pathname}")
    df = pd.read_csv(pathname, skiprows=1)  # Skip first row for raw CSV
    datetimes = []
    times = []
    values = []
    measurment_types = []
    
    for _, row in df.iterrows():
        datapoint_type = int(row.iloc[3])
        if datapoint_type == 0:
            datetime_str = row.iloc[2]
            value_str = row.iloc[4]
            dt = pd.to_datetime(datetime_str, format='%d-%m-%Y %H:%M')
            # dt = dt.tz_localize(MOSCOW_TZ)
            value = float(str(value_str).replace(',', '.'))
            datetimes.append(dt)
            times.append(dt.time())
            values.append(value)
            measurment_types.append(datapoint_type)
        if datapoint_type == 1:
            datetime_str = row.iloc[2]
            value_str = row.iloc[5]
            dt = pd.to_datetime(datetime_str, format='%d-%m-%Y %H:%M')
            # dt = dt.tz_localize(MOSCOW_TZ)
            value = float(str(value_str).replace(',', '.'))
            datetimes.append(dt)
            times.append(dt.time())
            values.append(value)
            measurment_types.append(datapoint_type)
    
    df = pd.DataFrame({
        'datetime': datetimes,
        'time': times,
        'value': values,
        'type': measurment_types
    })
    
    df = df.sort_values('datetime')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prepared_csv = os.path.join(OUTPUT_DIR, "prepared_dataset.csv")
    df.to_csv(prepared_csv, index=False)
    logging.info(f"Prepared data saved to {prepared_csv}")

    os.remove(pathname)
    logging.info(f"Original file {pathname} removed")

    return df, datetimes

def load_prepared_dataset():
    prepared_csv = os.path.join(OUTPUT_DIR, "prepared_dataset.csv")
    df = pd.read_csv(prepared_csv)  # No skiprows for prepared CSV
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.time
    return df, df['datetime'].tolist()

def plot_history(ds, return_fig=False):
    fig = make_subplots(
        rows=1, 
        cols=1,
        subplot_titles=('Исторические данные',)
    )

    assert len(ds['datetime']) != 0

    # Type 0
    mask = ds['type'] == 0
    fig.add_trace(
        go.Scatter(
            x=ds.loc[mask, 'datetime'],
            y=ds.loc[mask, 'value'],
            mode='lines+markers',
            name='Сканирование',
            marker=dict(
                symbol='diamond-tall',
                size=9,
                opacity=0.7
            ),
            line=dict(
                shape='spline',
                width=1,
                color='blue'
            ),
            hovertemplate=(
                "Дата и время: %{x|%Y-%m-%d %H:%M}<br>" +
                "Концентрация сахара: %{y:.1f} мМоль/литр<br>" +
                "Тип измерения: Сканирование<br>" +
                "<extra></extra>"
            )
        ),
        row=1, col=1
    )

    # Type 1
    mask = ds['type'] == 1
    fig.add_trace(
        go.Scatter(
            x=ds.loc[mask, 'datetime'],
            y=ds.loc[mask, 'value'],
            mode='markers',
            name='Ретроспективные данные',
            marker=dict(
                symbol='diamond-tall',
                size=9,
                opacity=0.7,
                color='darkcyan'
            ),
            hovertemplate=(
                "Дата и время: %{x|%Y-%m-%d %H:%M}<br>" +
                "Концентрация сахара: %{y:.1f} мМоль/литр<br>" +
                "Тип измерения: Ретроспективные данные<br>" +
                "<extra></extra>"
            )
        ),
        row=1, col=1
    )
    
    fig.update_layout(
        hovermode='closest',
        dragmode='zoom',
        margin={**COMMON_MARGIN, "l":60},
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    fig.update_yaxes(
        title_text="Сахар, мМоль/литр",
        title_font=dict(size=12),
        row=1, col=1
    )
     
    fig.update_xaxes(
        type='date',
        rangeslider=dict(
            visible=True,
            thickness=0.1,
        ),
        tickfont=dict(size=9),
        tickangle=0,
        row=1, col=1
    )
    
    if return_fig:
        return fig
    else:
        rendered_html = fig.to_html(config=CONFIG, include_plotlyjs=True, full_html=False)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(HISTORY_HTML, 'w') as file:
            file.write(rendered_html)
        logging.info(f"HTML file {HISTORY_HTML} was created!")
        return rendered_html

def plot_24h(ds, return_fig=False):
    fig = make_subplots(
        rows=1, 
        cols=1,
        subplot_titles=('Типичные сутки',)
    )

    assert len(ds['datetime']) != 0

    # Convert time to datetime for plotting
    ds['time'] = pd.to_datetime(ds['time'].astype(str), format='%H:%M:%S')

    mask = ds['type'] == 0
    scan_data = ds.loc[mask].copy()
    scan_data['time'] = scan_data['time'].dt.floor('15min')
    avg_data = scan_data.groupby('time').agg({
        'value': ['mean', 'std']
    }).reset_index()
    avg_data.columns = ['time', 'mean', 'std']

    # Plot average values with std ranges
    fig.add_trace(
        go.Scatter(
            x=avg_data['time'],
            y=avg_data['mean'],
            mode='lines+markers',
            name='Среднее по сканированию',
            marker=dict(
                symbol='circle',
                size=12,
                color='purple'
            ),
            line=dict(
                shape='spline',
                width=1,
                color='purple'
            ),
            hovertemplate=(
                "Время: %{x|%H:%M}<br>" +
                "Средняя концентрация: %{y:.1f} мМоль/литр<br>" +
                "Стандартное отклонение: %{customdata:.1f} мМоль/литр<br>" +
                "<extra></extra>"
            ),
            customdata=avg_data['std']
        ),
        row=1, col=1
    )

    # Add std ranges
    fig.add_trace(
        go.Scatter(
            x=avg_data['time'],
            y=avg_data['mean'] + avg_data['std'],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=avg_data['time'],
            y=avg_data['mean'] - avg_data['std'],
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(128,0,128,0.1)',
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )

    # Type 0: blue markers
    mask = ds['type'] == 0
    fig.add_trace(
        go.Scatter(
            x=ds.loc[mask, 'time'],
            y=ds.loc[mask, 'value'],
            mode='markers',
            name='Сканирование',
            marker=dict(
                symbol='diamond-tall',
                size=9,
                opacity=0.7,
                color='blue'
            ),
            hovertemplate=(
                "Дата и время: %{customdata|%Y-%m-%d %H:%M}<br>" +
                "Концентрация сахара: %{y:.1f} мМоль/литр<br>" +
                "Тип измерения: Сканирование<br>" +
                "<extra></extra>"
            ),
            customdata=ds.loc[mask, 'datetime']
        ),
        row=1, col=1
    )
    
    fig.update_layout(
        hovermode='closest',
        dragmode='zoom',
        margin={**COMMON_MARGIN, "l":60},
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    fig.update_yaxes(
        title_text="Сахар, мМоль/литр",
        title_font=dict(size=12),
        row=1, col=1
    )
     
    fig.update_xaxes(
        type='date',
        tickformat='%H:%M',
        tickfont=dict(size=9),
        tickangle=0,
        row=1, col=1
    )
    
    if return_fig:
        return fig
    else:
        rendered_html = fig.to_html(config=CONFIG, include_plotlyjs=True, full_html=False)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(AVERAGED_HTML, 'w') as file:
            file.write(rendered_html)
        logging.info(f"HTML file {AVERAGED_HTML} was created!")
        return rendered_html

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler()  # Log to console
        ]
    )

    # Check for raw CSV in input directory
    raw_csv = None
    for file in os.listdir(INPUT_DIR):
        filename = os.fsdecode(file)
        if filename.endswith(".csv"): 
            raw_csv = os.path.join(INPUT_DIR, filename)
            break

    if raw_csv:
        dataset, datetimes = prepare_dataset(raw_csv)
    else:
        dataset, datetimes = load_prepared_dataset()

    print(get_info_total(dataset)) 
    history_html = plot_history(dataset)
    averaged_html = plot_24h(dataset)
    
    with open(PLOTLY_COMBINED_HTML, 'w') as file:
        file.write(history_html)
        file.write(averaged_html)
        logging.info(f"HTML file {PLOTLY_COMBINED_HTML} created")
    webbrowser.open(Path(PLOTLY_COMBINED_HTML).absolute().as_uri())
