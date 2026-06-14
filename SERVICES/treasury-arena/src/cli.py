"""CLI interface for Treasury Arena Simulation Engine"""
import click
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from .simulation_engine import SimulationEngine, quick_backtest
from .simulation_results import SimulationResults, compare_runs, get_all_runs


@click.group()
def cli():
    """Treasury Arena Simulation CLI"""
    pass


@cli.command()
@click.option('--days', default=30, help='Number of days to backtest')
@click.option('--agents', default=10, help='Initial agent count')
@click.option('--speed', default=1.0, help='Time multiplier (1-1000x)')
def backtest(days, agents, speed):
    """Run a backtest simulation"""
    click.echo(f"Starting {days}-day backtest with {agents} agents...")
    
    results = asyncio.run(quick_backtest(days=days, agents=agents))
    
    click.echo("\n=== RESULTS ===")
    click.echo(f"Run ID: {results.run_id}")
    click.echo(f"Total Return: {results.total_return:.2f}%")
    click.echo(f"Sharpe Ratio: {results.sharpe_ratio:.2f}" if results.sharpe_ratio else "N/A")
    click.echo(f"Max Drawdown: {results.max_drawdown:.2f}%" if results.max_drawdown else "N/A")
    click.echo(f"Final Agents: {results.final_agents}")
    
    # Export to JSON
    output_file = f"results/{results.run_id}.json"
    Path("results").mkdir(exist_ok=True)
    results.to_json(output_file)
    click.echo(f"\nResults saved to: {output_file}")


@cli.command()
@click.argument('run_ids', nargs=-1, required=True)
def compare(run_ids):
    """Compare multiple simulation runs"""
    click.echo(f"Comparing {len(run_ids)} runs...")
    
    comparison = compare_runs(list(run_ids))
    
    click.echo("\n=== COMPARISON ===")
    for run in comparison['runs']:
        click.echo(f"\n{run['run_id']}:")
        click.echo(f"  Return: {run['total_return']:.2f}%")
        click.echo(f"  Sharpe: {run['sharpe_ratio']:.2f}" if run['sharpe_ratio'] else "N/A")
    
    click.echo(f"\nBest Return: {comparison['best_return']}")
    click.echo(f"Best Sharpe: {comparison['best_sharpe']}")


@cli.command()
def list():
    """List all simulation runs"""
    runs = get_all_runs()
    
    click.echo(f"\n{'Run ID':<25} {'Start':<12} {'End':<12} {'Return':<10} {'Agents':<8}")
    click.echo("-" * 75)
    
    for run in runs:
        click.echo(
            f"{run['run_id']:<25} "
            f"{run['start_date']:<12} "
            f"{run['end_date']:<12} "
            f"{run['total_return']:>8.2f}% "
            f"{run['final_agents']:>7}"
        )


if __name__ == '__main__':
    cli()
