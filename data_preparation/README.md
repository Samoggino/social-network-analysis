# Preparazione dei dati (fino alla fase pre-RQ1)

Ricostruisce le matrici di voto Eurovision di giuria e televoto e l'analisi
esplorativa iniziale, senza eseguire le Research Questions.

## 1. Prerequisiti

- Python 3.10 o successivo (su Windows: `py --version`)
- VS Code e terminale PowerShell (facoltativi)

## 2. Scaricare il dataset originale (non incluso)

- Aprire <https://github.com/EurovisionAPI/dataset>
- Premere *Code > Download ZIP*
- Estrarre l'archivio e mettere la cartella `dataset-main` in questa cartella,
  accanto a `build_eurovision_data.py`.
- Se si è estratta una cartella `dataset-main` dentro un'altra `dataset-main`,
  va bene: lo script riconosce entrambe le strutture.

## 3. Struttura prima dell'esecuzione

```text
data_preparation/
├── build_eurovision_data.py
├── validate_data.py
├── dataset-main/
│   └── data/senior/2016/...   (anche dataset-main/dataset-main è supportato)
└── src/
    └── exploratory_analysis.py
```

## 4. Generare le 20 matrici (nessuna libreria esterna)

Da un terminale in `data_preparation/`:

```bash
py build_eurovision_data.py
```

Risultato atteso con lo snapshot originale:

```text
Annual matrices: 20
Eligible national votes: 19698
Countries: 45
Done.
```

File generati:

- `processed_data/tables/votes_master.csv`
- `processed_data/tables/nodes.csv`
- `processed_data/matrices/2016_jury.csv` … `2026_public.csv`

Ogni riga delle matrici è un Paese votante, ogni colonna un Paese. Una cella
vuota indica un voto strutturalmente impossibile; uno zero indica un
destinatario ammissibile che non ha ricevuto punti. Voti positivi: 1–8, 10, 12.
Le 10 edizioni sono 2016–2019 e 2021–2026 (2020 annullato). I voti WLD (resto
del mondo) sono esclusi dal set di votanti nazionali.

## 5. Controllare le matrici

```bash
py validate_data.py
```

Deve stampare `VERIFICA RIUSCITA` e, con lo snapshot originale, 20 matrici,
19698 voti ammissibili, 45 Paesi. Il dataset GitHub è aggiornabile: eventuali
differenze vanno indagate, non corrette a mano per ottenere gli stessi conteggi.

## 6. Analisi esplorativa

```bash
py -m pip install networkx matplotlib
py src/exploratory_analysis.py
```

Risultato atteso con lo snapshot originale:

```text
Matrices read: 20
Country-level observations: 786
Completed. Source matrices were not modified.
```

File aggiuntivi:

- `results/exploratory/network_summary.csv`
- `results/exploratory/country_metrics.csv`
- `figures/exploratory/` (immagini illustrative)

## 7. Note di metodo

- Grafo orientato e pesato: votante → finalista, peso = punti.
- 0 non è un arco positivo; una cella vuota è un'opportunità inesistente.
- La validazione degli script è interna; il confronto indipendente con le
  fonti ufficiali Eurovision non è stato completato.
- Il dataset è di terze parti (EurovisionAPI), non una fonte EBU.
- Per confrontare esattamente gli output va usata la stessa revisione del
  repository: il download ZIP di GitHub cambia se il repository viene
  aggiornato.

Fonte: <https://github.com/EurovisionAPI/dataset>
