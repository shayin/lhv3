"""生成扫描结果的可视化图表

用法: PYTHONPATH=./ python3 scripts/plot_scan_results.py --summary data/scan_results/summary_full_20251001_211833.csv
"""
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def ensure_dir(p):
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', required=True)
    parser.add_argument('--outdir', default='data/scan_results/plots')
    args = parser.parse_args()

    ensure_dir(args.outdir)

    df = pd.read_csv(args.summary)

    # 确保 numeric
    for col in ['total_return', 'annual_return', 'max_drawdown']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 1) total_return 直方图
    if 'total_return' in df.columns:
        plt.figure(figsize=(8,5))
        plt.hist(df['total_return'].dropna(), bins=40, color='C0', edgecolor='k')
        plt.title('Distribution of Total Return')
        plt.xlabel('Total Return')
        plt.ylabel('Count')
        out1 = os.path.join(args.outdir, 'total_return_hist.png')
        plt.tight_layout()
        plt.savefig(out1)
        print('Saved', out1)
        plt.close()

    # 2) total_return vs max_drawdown 散点图
    if 'total_return' in df.columns and 'max_drawdown' in df.columns:
        plt.figure(figsize=(8,6))
        plt.scatter(df['max_drawdown'], df['total_return'], alpha=0.7, s=30)
        plt.title('Total Return vs Max Drawdown')
        plt.xlabel('Max Drawdown')
        plt.ylabel('Total Return')
        out2 = os.path.join(args.outdir, 'return_vs_drawdown.png')
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(out2)
        print('Saved', out2)
        plt.close()

    # 3) Top 20 by total_return bar
    if 'total_return' in df.columns:
        top20 = df.sort_values('total_return', ascending=False).head(20)
        plt.figure(figsize=(10,6))
        plt.bar(range(len(top20)), top20['total_return'], color='C2')
        plt.xticks(range(len(top20)), top20.index.astype(str), rotation=45)
        plt.title('Top 20 parameter sets by Total Return (index)')
        plt.ylabel('Total Return')
        out3 = os.path.join(args.outdir, 'top20_total_return.png')
        plt.tight_layout()
        plt.savefig(out3)
        print('Saved', out3)
        plt.close()

    print('Done')

if __name__ == '__main__':
    main()
