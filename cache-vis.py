# Filename: visualize_cache.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def load_data():
    """Load the cache latency data"""
    try:
        df = pd.read_csv('results/cache_latency.csv')
        print(f"Loaded cache latency data for: {list(df['cache_level'])}")
        return df
    except FileNotFoundError:
        print("Error: results/cache_latency.csv not found. Run the Rust program first!")
        return None

def create_latency_plot(df):
    """Create interactive latency plot with cache boundaries"""
    fig = px.bar(df, 
                 x='cache_level', 
                 y='latency_ns',
                 color='cache_level',
                 title='CPU Cache Hierarchy Latency (Pointer Chasing)',
                 labels={'latency_ns': 'Latency (ns)', 'cache_level': 'Cache Level'},
                 text_auto='.1f',
                 template='plotly_white')
    
    # Add cache boundary annotations
    fig.add_annotation(x=0.5, y=df['latency_ns'].max()*0.9,
                      text="L1 Cache (64KB)",
                      showarrow=True,
                      arrowhead=1,
                      ax=-50,
                      ay=-40)
    
    fig.add_annotation(x=1.5, y=df['latency_ns'].max()*0.7,
                      text="L2 Cache (512KB)",
                      showarrow=True,
                      arrowhead=1,
                      ax=0,
                      ay=-60)
    
    fig.add_annotation(x=3.5, y=df['latency_ns'].max()*0.5,
                      text="L3 Cache (64MB)",
                      showarrow=True,
                      arrowhead=1,
                      ax=0,
                      ay=-80)
    
    fig.update_layout(
        hovermode='x unified',
        yaxis_title='Latency (nanoseconds)',
        xaxis_title='Memory Hierarchy Level',
        showlegend=False,
        height=600
    )
    
    fig.write_html('results/cache_latency_interactive.html')
    print("Saved interactive plot to results/cache_latency_interactive.html")

def create_comparison_plot(df):
    """Create comparison plot showing latency jumps"""
    # Calculate latency multipliers
    df['multiplier'] = df['latency_ns'] / df['latency_ns'].iloc[0]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Latency bars
    fig.add_trace(
        go.Bar(
            x=df['cache_level'],
            y=df['latency_ns'],
            name='Latency (ns)',
            marker_color=px.colors.qualitative.Plotly,
            text=df['latency_ns'].round(1),
            textposition='outside'
        ),
        secondary_y=False
    )
    
    # Multiplier line
    fig.add_trace(
        go.Scatter(
            x=df['cache_level'],
            y=df['multiplier'],
            name='Latency Multiplier',
            mode='lines+markers+text',
            text=df['multiplier'].round(1),
            textposition='top center',
            line=dict(width=3),
            marker=dict(size=10)
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title_text='Cache Latency and Relative Performance Impact',
        xaxis_title='Memory Hierarchy Level',
        yaxis_title='Latency (nanoseconds)',
        yaxis2_title='Latency Multiplier (vs L1)',
        template='plotly_white',
        height=600,
        hovermode='x unified'
    )
    
    fig.write_html('results/cache_comparison_interactive.html')
    print("Saved comparison plot to results/cache_comparison_interactive.html")

def create_hierarchy_plot(df):
    """Create visual representation of cache hierarchy"""
    # Define cache sizes for visualization
    cache_sizes = {
        'L1': 64,
        'L2': 512,
        'L3': 64*1024,
        'RAM': 128*1024  # Assuming 128MB test size
    }
    
    fig = go.Figure()
    
    # Add cache level rectangles
    fig.add_shape(type="rect",
        x0=-0.5, y0=0, x1=0.5, y1=cache_sizes['L1'],
        fillcolor="lightgreen", opacity=0.5,
        layer="below", line_width=0
    )
    
    fig.add_shape(type="rect",
        x0=0.5, y0=0, x1=1.5, y1=cache_sizes['L2'],
        fillcolor="orange", opacity=0.5,
        layer="below", line_width=0
    )
    
    fig.add_shape(type="rect",
        x0=1.5, y0=0, x1=2.5, y1=cache_sizes['L3'],
        fillcolor="lightcoral", opacity=0.5,
        layer="below", line_width=0
    )
    
    fig.add_shape(type="rect",
        x0=2.5, y0=0, x1=3.5, y1=cache_sizes['RAM'],
        fillcolor="lightblue", opacity=0.5,
        layer="below", line_width=0
    )
    
    # Add latency markers
    for i, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[i],
            y=[row['latency_ns']],
            mode='markers+text',
            marker=dict(size=20, color='darkblue'),
            text=[f"{row['latency_ns']:.1f} ns"],
            textposition='top center',
            name=row['cache_level']
        ))
    
    fig.update_layout(
        title='CPU Cache Hierarchy Visualization',
        xaxis=dict(
            tickvals=list(range(len(df))),
            ticktext=df['cache_level'],
            title='Cache Level'
        ),
        yaxis=dict(
            title='Latency (ns)',
            range=[0, df['latency_ns'].max()*1.2]
        ),
        showlegend=False,
        height=600,
        template='plotly_white'
    )
    
    # Add cache size annotations
    fig.add_annotation(x=0, y=cache_sizes['L1'],
                       text="64KB",
                       showarrow=False,
                       yshift=10)
    
    fig.add_annotation(x=1, y=cache_sizes['L2'],
                       text="512KB",
                       showarrow=False,
                       yshift=10)
    
    fig.add_annotation(x=2, y=cache_sizes['L3'],
                       text="64MB",
                       showarrow=False,
                       yshift=10)
    
    fig.add_annotation(x=3, y=cache_sizes['RAM'],
                       text="RAM",
                       showarrow=False,
                       yshift=10)
    
    fig.write_html('results/cache_hierarchy_visualization.html')
    print("Saved hierarchy visualization to results/cache_hierarchy_visualization.html")

def main():
    print("CPU Cache Hierarchy Visualization")
    print("--------------------------------")
    
    df = load_data()
    if df is None:
        return
    
    print("\nCreating visualizations...")
    create_latency_plot(df)
    create_comparison_plot(df)
    create_hierarchy_plot(df)
    
    print("\nVisualization complete! Generated files:")
    print("- results/cache_latency_interactive.html")
    print("- results/cache_comparison_interactive.html")
    print("- results/cache_hierarchy_visualization.html")

if __name__ == "__main__":
    main()