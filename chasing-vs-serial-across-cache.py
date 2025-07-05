import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def load_data():
    try:
        df = pd.read_csv('results/cache_data.csv')
        print("Loaded data with columns:", df.columns.tolist())
        return df
    except FileNotFoundError:
        print("Error: results/cache_data.csv not found")
        return None

def create_comparison_plot(df):
    regions = [
        {'name': 'L1', 'color': 'rgba(100, 200, 100, 0.2)'},
        {'name': 'L1-L2', 'color': 'rgba(150, 200, 100, 0.15)'},
        {'name': 'L2', 'color': 'rgba(255, 200, 100, 0.2)'},
        {'name': 'L2-L3', 'color': 'rgba(255, 150, 100, 0.15)'},
        {'name': 'L3', 'color': 'rgba(255, 100, 100, 0.2)'},
        {'name': 'RAM', 'color': 'rgba(100, 100, 255, 0.2)'}
    ]
    
    fig = go.Figure()
    
    # Add pointer chasing line
    fig.add_trace(go.Scatter(
        x=df['cache_level'],
        y=df['pointer_chasing_ns'],
        mode='lines+markers',
        line=dict(width=4, color='red'),
        marker=dict(size=12, color='red'),
        name='Pointer Chasing',
        text=[f"{x:.2f} ns" for x in df['pointer_chasing_ns']],
        hoverinfo='text+name'
    ))
    
    # Add serial access line
    fig.add_trace(go.Scatter(
        x=df['cache_level'],
        y=df['serial_ns'],
        mode='lines+markers',
        line=dict(width=4, color='blue'),
        marker=dict(size=12, color='blue'),
        name='Serial Access',
        text=[f"{x:.2f} ns" for x in df['serial_ns']],
        hoverinfo='text+name'
    ))
    
    # Add cache regions
    for i, region in enumerate(regions):
        fig.add_vrect(
            x0=i-0.5, x1=i+0.5,
            fillcolor=region['color'],
            layer="below",
            line_width=0
        )
    
    fig.update_layout(
        title='<b>Memory Access Latency Comparison</b>',
        xaxis_title='Cache Level',
        yaxis_title='Latency (nanoseconds)',
        hovermode='x unified',
        plot_bgcolor='white',
        yaxis=dict(
            range=[0, max(df['pointer_chasing_ns'].max(), df['serial_ns'].max()) * 1.2],
            gridcolor='rgba(200,200,200,0.2)'
        ),
        xaxis=dict(
            type='category',
            gridcolor='rgba(200,200,200,0.2)'
        ),
        height=700,
        width=1000,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    fig.write_html('results/cache_comparison.html')
    print("Saved plot to results/cache_comparison.html")

def main():
    df = load_data()
    if df is not None:
        create_comparison_plot(df)

if __name__ == "__main__":
    main()