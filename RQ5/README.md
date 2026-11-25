# RQ5 — Previsione dei tre destinatari dei voti più alti

**Domanda.** Geografia, lingua e comunità di voto migliorano la previsione dei legami di voto forti nelle finali successive, una volta considerate la popolarità dei finalisti e la storia delle diadi?

Per ogni Paese votante e per ciascun sistema di voto, il modello ordina i finalisti ammissibili e seleziona i primi tre. Il bersaglio è l'insieme dei destinatari effettivi di **8, 10 e 12 punti**. La previsione è condizionata ai Paesi votanti e ai finalisti già noti prima della finale.

## Dati e protocollo temporale

- Dieci Grand Final, dal 2016 al 2026. Il 2020 è assente. Giurie e televoto nazionale sono separati e `WLD` è escluso.
- Le matrici sono in `../RQ1/processed_data/matrices/`. Celle vuote e zeri rappresentano rispettivamente voti impossibili e voti ammissibili senza punti. Il caricamento verifica anche la scala e la completezza delle schede.
- Gli attributi statici provengono da `../RQ2/processed_data/tables/country_attributes_rq2.csv`. La geografia è l'uguaglianza della sottoregione UN M49. La lingua indica almeno una famiglia in comune nell'insieme delle famiglie codificate per ciascun Paese.
- Si valutano **2023, 2024, 2025 e 2026** in ordine. Per ogni finale, lo storico include tutte le edizioni precedenti. Anche ogni riga usata per stimare i coefficienti ha feature costruite esclusivamente sulle edizioni precedenti a quella riga. Il 2016 e il 2017 forniscono solo storico. Scaling e regressione sono stimati sulle righe di addestramento.
- Il grafo e gli indici di ogni storico includono soltanto i Paesi che vi compaiono. Una diade senza un'opportunità storica usa i tassi di riferimento. Un Paese nuovo ha feature di comunità neutre. Il ranking riceve soltanto lo storico e la maschera di eleggibilità; i punti della finale da prevedere vengono letti per attribuire le metriche.

## Baseline e modelli

| Metodo | Informazioni usate |
|---|---|
| Casuale | Tre finalisti ammissibili uniformi. Hit@3 atteso pari a `3/n` per scheda |
| History | Media regolarizzata dei punti della diade, con popolarità storica come secondo criterio |
| M0a | Tasso storico con cui il finalista riceve voti forti |
| M0b | M0a più tasso storico di voti forti, punti medi della diade e tasso di voti forti nella direzione inversa |
| M1 | M0b più sottoregione condivisa e almeno una famiglia linguistica comune |
| M2 | M1 più appartenenza alla stessa comunità Louvain e coesione interna della comunità |

I tassi storici sono `(conteggio + 5 × tasso globale) / (opportunità + 5)`. La media dei punti usa la media globale come riferimento analogo. La coesione è il tasso interno regolarizzato di voti forti meno il tasso globale e vale zero fra comunità diverse. M0a–M2 usano una logistica L2 con penalità 1 sulle feature standardizzate e intercetta libera. La penalità e la costante di smoothing (5) sono fissate a priori, senza una validazione temporale interna. Il solver verifica la convergenza di ogni fit prima di generare gli output. L'ordinamento usa il punteggio logit, che preserva l'ordine delle probabilità.

Per i pari merito residui si usa la priorità di un hash SHA-256 del seme, dell'edizione e dei due Paesi. La stessa priorità vale per tutti i metodi sulla stessa scheda ed è indipendente dai voti osservati. Si registra il numero di pari merito sulla soglia del terzo posto e si conserva un confronto diagnostico con l'ordine originale delle colonne.

### Comunità e coerenza con RQ2

Per M2 si sommano i punti dei due versi su un grafo non orientato, separatamente per layer e storico. Su quel grafo si sceglie la partizione con modularità massima fra dieci avvii Louvain. Il test di sensibilità usa le funzioni di RQ2 per stimare, sullo stesso grafo storico, il consenso di **200 avvii** mediante co-assegnazioni, raggruppamento gerarchico e numero modale di comunità. Il consenso è ricalcolato per gli storici delle righe di addestramento e del test. Le etichette di RQ2 pubblicate nei CSV non entrano in RQ5. RQ2 usa reti annuali, mentre qui la proiezione è aggregata sul passato per consentire la previsione.

## Valutazione

- **Hit@3** è la frazione dei tre destinatari effettivi recuperata tra i primi tre. Su ogni scheda coincide con precisione e richiamo al terzo posto.
- **NDCG@3** attribuisce più peso alle posizioni iniziali e usa rilevanza binaria. **MRR** usa l'inverso della posizione del primo destinatario effettivo nell'intero ranking. Le metriche trattano 8, 10 e 12 punti come la stessa classe di rilevanza.
- Le medie danno lo stesso peso alle quattro finali. I confronti sono appaiati sulle stesse schede e presentati per finale. Si controlla la sensibilità omettendo una finale alla volta dal riepilogo, senza ripetere l'addestramento, e separando il recupero dei destinatari con e senza opportunità storiche.
- I risultati sono descrittivi per le quattro finali di test. Il riepilogo usa differenze, copertura e variazione fra edizioni. Le finestre di addestramento sovrapposte e i votanti ricorrenti limitano l'inferenza su nuove edizioni.

## Risultati

Medie a pesi uguali sulle quattro finali di test.

| Modello | Hit@3 giurie | NDCG@3 giurie | MRR giurie | Hit@3 televoto | NDCG@3 televoto | MRR televoto |
|---|---:|---:|---:|---:|---:|---:|
| Casuale | 0,121 | — | — | 0,121 | — | — |
| History | 0,2461 | 0,2658 | 0,5178 | 0,4160 | 0,4543 | 0,7299 |
| M0a | 0,2344 | 0,2409 | 0,4737 | 0,2103 | 0,2379 | 0,5078 |
| M0b | 0,2461 | 0,2599 | 0,4942 | 0,4273 | 0,4632 | 0,7261 |
| M1 | 0,2553 | 0,2708 | 0,5100 | 0,4297 | 0,4580 | 0,7063 |
| M2 | 0,2441 | 0,2664 | 0,5203 | 0,4322 | 0,4621 | 0,7101 |

- **Storico.** Per il televoto, M0b supera M0a di **+0,2171** in Hit@3 medio e prevale in tutte e quattro le finali. Il guadagno resta fra **+0,1903 e +0,2534** omettendo una finale alla volta. La regola semplice History raggiunge già **0,4160**. M0b la supera di **+0,0114** in tre finali su quattro e migliora NDCG@3, mentre History ottiene il miglior MRR medio. Per le giurie, il guadagno di M0b su M0a è **+0,0116** e M0b e History hanno lo stesso Hit@3 medio. Per M0b soltanto 9 destinatari forti delle giurie e 7 del televoto non avevano opportunità storiche. Nessuno di questi è stato recuperato e i denominatori sono piccoli.
- **Geografia e lingua.** Insieme aggiungono **+0,0093** per le giurie e **+0,0024** per il televoto rispetto a M0b. Il confronto riguarda il blocco congiunto. Per il televoto la direzione del guadagno dipende da quale finale si omette.
- **Comunità.** M2 rispetto a M1 cambia Hit@3 di **−0,0113** per le giurie e **+0,0025** per il televoto. Con il consenso, la differenza rispetto al M2 principale è **+0,0023** per le giurie e **−0,0068** per il televoto. Rispetto a M1, anche il consenso produce un piccolo saldo negativo in entrambi i layer. Questi risultati riguardano le quattro finali osservate. Restano aperti il contributo delle comunità in altre edizioni e quello di altre definizioni o feature.

### Diagnostica

I **40 fit** sono convergenti in **6–7 iterazioni**, con norma del gradiente al massimo di circa **4,94 × 10⁻¹³**. I sette test automatici passano. Due esecuzioni nell'ambiente di riferimento producono CSV, registro e PNG identici byte per byte.

## Riproduzione

Ambiente di riferimento Python 3.12 con le versioni in `requirements.txt`. Dalla cartella RQ5 nel repository:

```bash
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B src/analyze_rq5_prediction.py
```

Per usare input in un'altra posizione indicare `--matrices`, `--attributes` e `--rq2-src`. `--output-dir` consente di scegliere una diversa radice per i risultati.

| Output in `results/rq5/` | Contenuto |
|---|---|
| `rq5_predictions_by_year.csv` | Baseline History, quattro modelli, tre metriche e parità in soglia |
| `rq5_model_comparison.csv` | Confronti Hit@3 appaiati, medie e differenze annuali |
| `rq5_fold_diagnostics.csv` | Anni, schede, positivi, modularità e dimensione delle partizioni |
| `rq5_coefficients.csv` | Coefficienti delle feature standardizzate, inclusa la sensibilità M2 |
| `rq5_fit_diagnostics.csv` | Iterazioni, convergenza e norma infinito del gradiente |
| `rq5_robustness.csv` | Esclusioni per finale, copertura storica, confronto tra procedure di spareggio e sensibilità al consenso |
| `rq5_run_config.json` | Semi, parametri, fold, versioni e SHA-256 degli input |

Il grafico in `figures/rq5/` mostra un punto per finale e un tratto per la media. La linea tratteggiata è l'attesa casuale media.
