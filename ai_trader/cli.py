import click

@click.group()
def cli():
    """A CLI tool for the AI Trader application."""
    pass

@cli.command()
@click.argument('symbols', nargs=-1, required=True)
@click.option('--exchange', type=click.Choice(['yahoo', 'binance']), required=True, help='Exchange to fetch from.')
@click.option('--start-date', type=str, help='Start date for data fetching (YYYY-MM-DD).')
@click.option('--end-date', type=str, help='End date for data fetching (YYYY-MM-DD).')
@click.option('--period', type=str, help='Period to fetch if start/end date not given (e.g., 1mo, 1y, max).')
@click.option('--interval', type=str, default='1d', help='Data interval (e.g., 1m, 5m, 15m, 1h, 1d).')
@click.option('--dry-run', is_flag=True, help='Simulate fetching and saving without writing to DB.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging.')
def fetch_data(symbols, exchange, start_date, end_date, period, interval, dry_run, verbose):
    """Fetches OHLCV data from exchanges and stores it in the database."""
    from scripts.fetch_price_data import main as fetch_main
    # This is a bit of a hack. A better way would be to refactor the script
    # into a function that can be called with arguments.
    import sys
    sys.argv = ['scripts/fetch_price_data.py', *symbols]
    if exchange:
        sys.argv.extend(['--exchange', exchange])
    if start_date:
        sys.argv.extend(['--start_date', start_date])
    if end_date:
        sys.argv.extend(['--end_date', end_date])
    if period:
        sys.argv.extend(['--period', period])
    if interval:
        sys.argv.extend(['--interval', interval])
    if dry_run:
        sys.argv.append('--dry-run')
    if verbose:
        sys.argv.append('--verbose')
    fetch_main()

@cli.command()
@click.option('--symbol', type=str, required=True, help='Asset symbol (e.g., BTC-USD, AAPL).')
@click.option('--start-date', type=str, help='Start date for processing (YYYY-MM-DD).')
@click.option('--end-date', type=str, help='End date for processing (YYYY-MM-DD).')
@click.option('--dry-run', is_flag=True, help='Simulate processing without writing to DB.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging.')
def process_features(symbol, start_date, end_date, dry_run, verbose):
    """Calculates technical features from PriceData and stores them."""
    from ai_trader.data_pipeline import main as pipeline_main
    import sys
    sys.argv = ['ai_trader/data_pipeline.py']
    if symbol:
        sys.argv.extend(['--symbol', symbol])
    if start_date:
        sys.argv.extend(['--start_date', start_date])
    if end_date:
        sys.argv.extend(['--end_date', end_date])
    if dry_run:
        sys.argv.append('--dry-run')
    if verbose:
        sys.argv.append('--verbose')
    pipeline_main()

if __name__ == '__main__':
    cli()
