"""Connection-local population selection; legacy databases retain prior behavior."""
def install_population(conn, *, legacy_all=False, require_complete=False):
    tables = {r[0] for r in conn.execute("SELECT name FROM main.sqlite_master WHERE type='table'")}
    if 'release_manifest' in tables:
        row = conn.execute('SELECT status FROM release_manifest').fetchall()
        if require_complete and row != [('complete',)]:
            raise ValueError('Release is incomplete')
        selection = 'SELECT barcode FROM main.release_population'
    elif 'population_membership' in tables:
        if require_complete:
            raise ValueError('Ingestion copy has no completed downstream release')
        selection = "SELECT barcode FROM main.population_membership WHERE membership='retained'"
    elif legacy_all:
        selection = 'SELECT barcode FROM main.products'
    else:
        selection = ('SELECT barcode FROM main.products WHERE ingested_at = '
                     '(SELECT MAX(ingested_at) FROM main.products) OR '
                     '(SELECT MAX(ingested_at) FROM main.products) IS NULL')
    conn.execute('CREATE TEMP VIEW IF NOT EXISTS current_product_barcodes AS ' + selection)
