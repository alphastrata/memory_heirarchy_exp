# Filename: visualize.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def load_data():
    """Load both latency datasets"""
    try:
        pc_df = pd.read_csv('results/latency_pointer_chasing.csv')
        seq_df = pd.read_csv('results/latency_sequential.csv')
        pc_df['type'] = 'Pointer Chasing'
        seq_df['type'] = 'Sequential'
        combined = pd.concat([pc_df, seq_df])
        print(f"Loaded {len(combined)} data points")
        return combined
    except FileNotFoundError:
        print("Error: CSV files not found. Run the Rust program first!")
        return None

def detect_cache_levels(df):
    """Detect cache level boundaries using change point detection"""
    # Use pointer chasing data for detection as it shows true hierarchy
    pc_df = df[df['type'] == 'Pointer Chasing']
    sizes = pc_df['data_size_kb'].values
    latencies = pc_df['latency_ns'].values
    
    # Smooth the data slightly to reduce noise
    from scipy.signal import savgol_filter
    smoothed = savgol_filter(latencies, window_length=min(11, len(latencies)//3), polyorder=2)
    
    # Find significant jumps (>50% increase)
    boundaries = []
    threshold = 1.5  # 50% increase threshold
    
    for i in range(1, len(smoothed)):
        if smoothed[i] > smoothed[i-1] * threshold:
            boundaries.append({
                'size_kb': sizes[i],
                'size_mb': sizes[i] / 1024,
                'latency': latencies[i],
                'level': len(boundaries) + 1
            })
    
    return boundaries

def create_cache_hierarchy_plot(df, boundaries):
    """Create dedicated cache hierarchy plot with MB scaling"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot both access patterns
    sns.lineplot(data=df, x='data_size_kb', y='latency_ns', hue='type',
                linewidth=2, marker='o', markersize=6, ax=ax)
    
    # Add cache boundaries
    for i, boundary in enumerate(boundaries):
        color = f'C{i+1}'
        ax.axvline(x=boundary['size_kb'], color=color, linestyle='--', alpha=0.7)
        
        # Format label based on size
        if boundary['size_kb'] > 1024:  # Use MB for L3 and beyond
            label = f"L{boundary['level']} Cache\n{boundary['size_mb']:.1f} MB"
        else:
            label = f"L{boundary['level']} Cache\n{boundary['size_kb']:.0f} KB"
            
        ax.text(boundary['size_kb'], ax.get_ylim()[1]*0.8, label,
               rotation=90, ha='right', va='top', fontsize=10, color=color)
    
    # Set log scale and format x-axis
    ax.set_xscale('log')
    ax.set_xlabel('Data Size (KB/MB)', fontsize=12)
    ax.set_ylabel('Latency (ns)', fontsize=12)
    ax.set_title('Memory Hierarchy Access Patterns', fontsize=14, fontweight='bold')
    
    # Custom x-axis ticks showing both KB and MB
    locs = [1, 10, 100, 1024, 10*1024, 100*1024]
    labels = ['1 KB', '10 KB', '100 KB', '1 MB', '10 MB', '100 MB']
    ax.set_xticks(locs)
    ax.set_xticklabels(labels)
    
    ax.grid(True, alpha=0.3)
    ax.legend(title='Access Pattern')
    
    plt.tight_layout()
    plt.savefig('results/cache_hierarchy_detailed.png', dpi=300, bbox_inches='tight')
    print("Saved cache hierarchy plot to results/cache_hierarchy_detailed.png")

def create_comparison_plot(df, boundaries):
    """Create plot comparing prefetch impact by cache level"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create cache level masks
    masks = []
    prev_size = 0
    for boundary in boundaries:
        masks.append((prev_size, boundary['size_kb']))
        prev_size = boundary['size_kb']
    masks.append((prev_size, df['data_size_kb'].max()))  # Main memory
    
    # Calculate average latencies for each region
    results = []
    for i, (start, end) in enumerate(masks):
        region_df = df[(df['data_size_kb'] >= start) & (df['data_size_kb'] < end)]
        for pattern in ['Pointer Chasing', 'Sequential']:
            avg_lat = region_df[region_df['type'] == pattern]['latency_ns'].mean()
            level = f'L{i+1}' if i < len(boundaries) else 'RAM'
            results.append({
                'Level': level,
                'Pattern': pattern,
                'Latency': avg_lat,
                'Size': (start + end)/2
            })
    
    # Create dataframe and plot
    plot_df = pd.DataFrame(results)
    sns.barplot(data=plot_df, x='Level', y='Latency', hue='Pattern', ax=ax)
    
    ax.set_title('Average Latency by Cache Level and Access Pattern', fontsize=14)
    ax.set_xlabel('Memory Hierarchy Level', fontsize=12)
    ax.set_ylabel('Average Latency (ns)', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/cache_level_comparison.png', dpi=300)
    print("Saved cache level comparison plot to results/cache_level_comparison.png")

def create_matplotlib_plots(df, boundaries):
    """Create all matplotlib plots"""
    print("\nCreating matplotlib plots...")
    create_cache_hierarchy_plot(df, boundaries)
    create_comparison_plot(df, boundaries)
    
    # Existing plots (from original code)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Linear scale
    sns.lineplot(data=df, x='data_size_kb', y='latency_ns', hue='type', ax=ax1)
    ax1.set_xlabel('Data Size (KB)', fontsize=12)
    ax1.set_ylabel('Latency (ns)', fontsize=12)
    ax1.set_title('Memory Access Latency (Linear Scale)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Log scale
    sns.lineplot(data=df, x='data_size_kb', y='latency_ns', hue='type', ax=ax2)
    ax2.set_xscale('log')
    ax2.set_xlabel('Data Size (KB, log scale)', fontsize=12)
    ax2.set_ylabel('Latency (ns)', fontsize=12)
    ax2.set_title('Memory Access Latency (Log Scale)', fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Latency distributions
    sns.histplot(data=df, x='latency_ns', hue='type', bins=50, ax=ax3)
    ax3.set_xlabel('Latency (ns)', fontsize=12)
    ax3.set_ylabel('Frequency', fontsize=12)
    ax3.set_title('Latency Distribution', fontsize=14)
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Cache regions
    colors = ['green', 'orange', 'red', 'purple', 'brown']
    prev_size = 0
    for i, boundary in enumerate(boundaries):
        mask = (df['data_size_kb'] >= prev_size) & (df['data_size_kb'] < boundary['size_kb'])
        if mask.any():
            region_df = df[mask]
            sns.lineplot(data=region_df, x='data_size_kb', y='latency_ns', hue='type',
                        ax=ax4, palette=[colors[i % len(colors)]], 
                        label=f'L{boundary["level"]} Cache')
        prev_size = boundary['size_kb']
    
    # Main memory
    mask = df['data_size_kb'] >= prev_size
    if mask.any():
        sns.lineplot(data=df[mask], x='data_size_kb', y='latency_ns', hue='type', ax=ax4)
    
    ax4.set_xlabel('Data Size (KB)', fontsize=12)
    ax4.set_ylabel('Latency (ns)', fontsize=12)
    ax4.set_title('Memory Hierarchy Regions', fontsize=14)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/memory_hierarchy_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved comprehensive analysis plots to results/memory_hierarchy_analysis.png")

def main():
    """Main analysis pipeline"""
    print("Memory Hierarchy Visualization Analysis")
    print("-------------------------------------")
    
    df = load_data()
    if df is None:
        return
    
    boundaries = detect_cache_levels(df)
    print(f"\nDetected {len(boundaries)} cache level boundaries:")
    for boundary in boundaries:
        if boundary['size_kb'] > 1024:
            print(f"  L{boundary['level']} Cache: up to {boundary['size_mb']:.1f} MB ({boundary['latency']:.1f} ns)")
        else:
            print(f"  L{boundary['level']} Cache: up to {boundary['size_kb']:.0f} KB ({boundary['latency']:.1f} ns)")
    
    create_matplotlib_plots(df, boundaries)
    
    print("\nAnalysis complete! Generated plots:")
    print("- results/cache_hierarchy_detailed.png (Main hierarchy plot)")
    print("- results/cache_level_comparison.png (Latency by level)")
    print("- results/memory_hierarchy_analysis.png (Comprehensive analysis)")

if __name__ == "__main__":
    main()