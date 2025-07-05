import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re

def load_data():
    try:
        df = pd.read_csv('results/cache_data.csv')
        print("Loaded data with columns:", df.columns.tolist())
        return df
    except FileNotFoundError:
        print("Error: results/cache_data.csv not found")
        return None

def update_readme_table(df, readme_path='README.md'):
    # Prepare new table with % increase vs L1
    l1_latency = df.iloc[0]['pointer_chasing_ns']
    table = "| Level    | Size (MB) | Pointer Chasing (ns) | Serial (ns) | % Increase vs L1 |\n"
    table += "|----------|-----------|----------------------|-------------|------------------|\n"
    for i, row in df.iterrows():
        size_mb = row['allocated_bytes'] / (1024*1024)
        pct = 0.0 if i == 0 else ((row['pointer_chasing_ns'] - l1_latency) / l1_latency) * 100
        table += f"| {row['cache_level']:<8} | {size_mb:6.2f}    | {row['pointer_chasing_ns']:.2f}                 | {row['serial_ns']:.2f}        | {pct:8.1f}%         |\n"
    # Read README
    with open(readme_path, 'r') as f:
        content = f.read()
    # Replace the table (from the table header to the next blank line)
    new_content = re.sub(
        r'(\| Level[\s\S]+?\| RAM[\s\S]+?\|)(\n|\r|\r\n)',
        table + '\n',
        content,
        count=1
    )
    with open(readme_path, 'w') as f:
        f.write(new_content)
    print("Updated README.md with new measured values and % increase column.")

def create_comparison_plot(df):
    regions = [
        {'name': 'L1', 'color': 'rgba(100, 200, 100, 0.2)'},
        {'name': 'L1-L2', 'color': 'rgba(150, 200, 100, 0.15)'},
        {'name': 'L2', 'color': 'rgba(255, 200, 100, 0.2)'},
        {'name': 'L2-L3', 'color': 'rgba(255, 150, 100, 0.15)'},
        {'name': 'L3', 'color': 'rgba(255, 100, 100, 0.2)'},
        {'name': 'RAM', 'color': 'rgba(100, 100, 255, 0.2)'}
    ]

    # Decide scale for allocated_bytes (KB or MB)
    max_bytes = df['allocated_bytes'].max()
    if max_bytes >= 1024*1024:
        alloc_div = 1024*1024
        alloc_unit = 'MB'
        alloc_vals = df['allocated_bytes'] / alloc_div
        alloc_text = [f"{x/1024/1024:.2f} MB" for x in df['allocated_bytes']]
        yaxis2_tickformat = '.2f'
    else:
        alloc_div = 1024
        alloc_unit = 'KB'
        alloc_vals = df['allocated_bytes'] / alloc_div
        alloc_text = [f"{x/1024:.1f} KB" for x in df['allocated_bytes']]
        yaxis2_tickformat = '.1f'

    fig = go.Figure()

    # Add pointer chasing line (left y-axis)
    fig.add_trace(go.Scatter(
        x=df['cache_level'], y=df['pointer_chasing_ns'], mode='lines+markers',
        line=dict(width=4, color='red'), marker=dict(size=12, color='red'),
        name='Pointer Chasing', text=[f"{x:.2f} ns" for x in df['pointer_chasing_ns']],
        hoverinfo='text+name', yaxis='y1'))
    # Add serial access line (left y-axis)
    fig.add_trace(go.Scatter(
        x=df['cache_level'], y=df['serial_ns'], mode='lines+markers',
        line=dict(width=4, color='blue'), marker=dict(size=12, color='blue'),
        name='Serial Access', text=[f"{x:.2f} ns" for x in df['serial_ns']],
        hoverinfo='text+name', yaxis='y1'))
    # Add allocated bytes as a bar/line on the right y-axis
    fig.add_trace(go.Bar(
        x=df['cache_level'], y=alloc_vals, name=f'Allocated ({alloc_unit})',
        marker_color='rgba(50, 50, 200, 0.5)', yaxis='y2', opacity=0.5,
        text=alloc_text, hoverinfo='text+name'))

    # Add cache regions
    for i, region in enumerate(regions):
        fig.add_vrect(
            x0=i-0.5, x1=i+0.5,
            fillcolor=region['color'], layer="below", line_width=0
        )

    fig.update_layout(
        title='<b>Memory Access Latency Comparison</b>',
        xaxis_title='Cache Level',
        yaxis=dict(
            title='Latency (ns)',
            range=[0, max(df['pointer_chasing_ns'].max(), df['serial_ns'].max()) * 1.2],
            gridcolor='rgba(200,200,200,0.2)',
            tickformat=',.0f ns',
            showgrid=True,
            zeroline=True,
            zerolinecolor='rgba(200,200,200,0.5)'
        ),
        yaxis2=dict(
            title=f'Allocated ({alloc_unit})',
            overlaying='y',
            side='right',
            showgrid=False,
            tickformat=yaxis2_tickformat,
        ),
        xaxis=dict(
            type='category',
            gridcolor='rgba(200,200,200,0.2)'
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        height=700,
        width=1000,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(t=100)
    )

    # Save interactive plot
    fig.write_html('results/cache_comparison_all.html')
    print("Saved interactive plot to results/cache_comparison_all.html")

    # --- Matplotlib PNG plot ---
    fig2, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    ax1.plot(df['cache_level'], df['pointer_chasing_ns'], 'o-r', label='Pointer Chasing')
    ax1.plot(df['cache_level'], df['serial_ns'], 'o-b', label='Serial Access')
    ax1.set_ylabel('Latency (ns)')
    ax1.set_xlabel('Cache Level')
    ax2.bar(df['cache_level'], df['allocated_bytes'] / (1024*1024), alpha=0.3, color='purple', label='Allocated (MB)')
    ax2.set_ylabel('Allocated (MB)')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.title('Memory Access Latency and Allocation')
    plt.tight_layout()
    plt.savefig('results/cache_comparison_all.png', dpi=300)
    print("Saved PNG plot to results/cache_comparison_all.png")

def main():
    df = load_data()
    if df is not None:
        create_comparison_plot(df)
        update_readme_table(df)

if __name__ == "__main__":
    main()