# RQ4 — Somiglianza dei Layer e Stabilità Temporale

**Domanda di ricerca.** Giurie e televoto esprimono strutture di voto simili nella stessa edizione? E quanto è stabile la stessa struttura (giurie o televoto) tra edizioni consecutive?

## Dati e convenzioni

- 10 edizioni: Grand Final 2016–2026 (2020 cancellata), layer *jury* e *public* mantenuti separati, WLD escluso.
- Matrici di input: `../RQ1/processed_data/matrices/` (identiche a quelle usate da RQ1, RQ2, RQ3). `W[i, j]` = punti dal votante *i* al finalista *j*; cella vuota = voto impossibile; 0 = voto ammissibile senza punti.
- Le maschere di eleggibilità sono **identiche tra i due layer in ogni edizione** (850–1092 celle per anno). Il codice verifica l'intersezione invece di assumere l'identità.

Due distinzioni metodologiche guidano tutta l'analisi:

1. **Celle comuni**. Un confronto entra solo nelle diadi che sono voti ammissibili in *entrambe* le reti confrontate. Nelle matrici Eurovision l'eleggibilità coincide tra jury e public dello stesso anno, ma lo script non lo dà per scontato.
2. **QAP**. La correlazione tra due reti che condividono i nodi non è un campione di diadi indipendenti: righe e colonne sono gli stessi paesi, quindi la dimensione campionaria effettiva è molto minore del numero di celle. I p-value sono calcolati permutando le etichette dei paesi di una rete (righe e colonne insieme) e ricalcolando la statistica sulle celle che restano ammissibili in entrambe. La statistica osservata è calcolata nello stesso modo, sull'intersezione delle due maschere, così che valori osservati e permutati siano confrontabili. Questa è la procedura di Quadratic Assignment nominata nella proposta.

## Metodi

### 1. Somiglianza tra layer (stesso anno) — `analyze_rq4_layer_similarity.py`

Per ogni edizione le due reti sono confrontate sulle diadi ammissibili in entrambe. Quattro quantità:

| Statistic | Descrizione |
|---|---|
| `spearman` | Correlazione di Spearman dei punti su tutte le diadi comuni. Attenzione: circa metà delle celle ammissibili sono zeri in entrambi i layer, e l'accordo sugli zeri la gonfia. |
| `pearson` | Correlazione di Pearson sugli stessi punti, per confronto. |
| `residual_pearson` | Correlazione di Pearson dopo aver rimosso gli effetti di livello votante e destinatario. Il residuo di una cella è i suoi punti meno la media del suo votante, meno la media del suo destinatario, più la media globale, tutto calcolato sulle celle mascherate. Ciò che resta è la parte dello scambio non spiegata da quanto è generoso il votante o da quanto è popolare il destinatario, ovvero l'allineamento delle coppie effettive. Se i layer concordassero solo su quali paesi sono popolari, questa correlazione sarebbe vicina a zero mentre quella grezza resterebbe alta. |
| `jaccard` | Indice di Jaccard tra i due insiemi di diadi positive (entrambi i layer danno punti > 0), ignorando l'entità dei punteggi. |

Una quinta quantità è calcolata ma secondaria: `spearman_both_positive`, la correlazione di Spearman ristretta alle diadi dove *entrambi* i layer hanno dato punti. Risponde a "quando entrambi concordano che c'è uno scambio, concordano sulla sua entità?", su un sottoinsieme molto più piccolo e non casuale.

Tutti i p-value sono QAP: le etichette dei paesi di un layer sono permutate (righe e colonne insieme), 1000 volte, e la statistica è ricalcolata sulle celle che restano ammissibili in entrambe le reti.

### 2. Stabilità temporale (stesso layer, edizioni diverse) — `analyze_rq4_temporal_stability.py`

La stessa rete è messa a confronto con se stessa in edizioni diverse. Per ogni lag da 1 a 9 edizioni, le due reti sono allineate sui paesi presenti in entrambe, e il confronto è calcolato sulle diadi che erano voti ammissibili in entrambe le edizioni. Il lag è misurato in edizioni e non in anni: 2020 manca, quindi un lag di 1 è sempre l'edizione successiva (2019 → 2021 compreso).

Le stesse quattro statistiche (`spearman`, `pearson`, `residual_pearson`, `jaccard`) sono calcolate per ogni coppia di edizioni. La statistica riportata per un lag è la media sulle coppie con quel lag. Il suo p-value deriva da un nullo che permuta le etichette dei paesi di un anno indipendentemente dentro ogni coppia e poi media nello stesso modo: il nullo si riferisce quindi alla statistica media, non a una singola coppia.

Il confronto lag-1 tra jury e public è testato con il test esatto *sign-flip* accoppiato sulle 9 coppie consecutive di edizioni: dentro ogni coppia si scambiano i due layer e si guarda quanti dei 2⁹ = 512 scambi producono una differenza almeno tanto grande quanto l'osservata.

**Relazione con RQ1**. RQ1 misura la persistenza di coppie reciproche individuali e di configurazioni triadiche con un modello temporale nullo (MCMC edge-swap per rete). L'unità qui è diversa: matrici intere, pesate, con effetti di votante e destinatario rimossi. Le due analisi rispondono a domande diverse e vanno lette insieme.

## Risultati

### Somiglianza tra layer (stesso anno)

| Statistic | Media 10 edizioni | Min | Max | Nullo (media) | q95 nullo | Significative (p<0.05) |
|---|---:|---:|---:|---:|---:|---:|
| Spearman | 0.311 | 0.181 | 0.468 | −0.002 | 0.200 | 10/10 |
| Pearson | 0.329 | 0.191 | 0.475 | −0.001 | 0.205 | 10/10 |
| Residual Pearson | 0.241 | 0.167 | 0.314 | +0.000 | 0.083 | 10/10 |
| Jaccard | 0.384 | 0.323 | 0.471 | 0.249 | 0.349 | 10/10 |
| Spearman (entrambi > 0) | 0.191 | 0.064 | 0.351 | — | — | 3/10 |

- La correlazione grezza (Spearman/Pearson ~0.3) è significativa in tutti e 10 gli anni contro il nullo QAP, ma è in parte guidata dall'accordo su quali paesi sono popolari.
- La **residual Pearson (0.241)** rimuove esattamente quell'effetto e resta significativa 10/10, con un nullo molto più stretto (q95 0.083). L'allineamento delle coppie *reali* è quindi reale e non si riduce a "entrambi votano gli stessi paesi popolari".
- **Jaccard (0.384)** è ben sopra il nullo (0.249), confermando che gli stessi *tipi* di scambi (chi vota chi) ricorrono nei due layer.
- La correlazione ristretta alle diadi dove entrambi danno punti (Spearman 0.191, solo 3/10 significative) dice che quando entrambi concordano che c'è uno scambio, l'entità dei punti è poco allineata.

### Stabilità temporale (stesso layer, edizioni diverse)

| Layer | Lag | Coppie | Spearman medio | Nullo medio | q95 nullo | p | Residual Pearson medio | Jaccard medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jury | 1 | 9 | 0.099 | 0.002 | 0.087 | 0.024 | 0.118 | 0.292 |
| Public | 1 | 9 | 0.263 | 0.002 | 0.109 | 0.002 | 0.471 | 0.359 |
| Jury | 2 | 8 | 0.144 | −0.001 | 0.092 | 0.006 | 0.119 | 0.320 |
| Public | 2 | 8 | 0.270 | 0.006 | 0.136 | 0.002 | 0.462 | 0.354 |
| Jury | 3 | 7 | 0.171 | 0.001 | 0.097 | 0.002 | 0.104 | 0.325 |
| Public | 3 | 7 | 0.341 | 0.000 | 0.133 | 0.002 | 0.434 | 0.397 |
| Jury | 4 | 6 | 0.148 | −0.002 | 0.104 | 0.006 | 0.069 | 0.310 |
| Public | 4 | 6 | 0.243 | −0.010 | 0.162 | 0.006 | 0.430 | 0.352 |
| Jury | 5 | 5 | 0.167 | 0.001 | 0.096 | 0.004 | 0.088 | 0.318 |
| Public | 5 | 5 | 0.246 | 0.001 | 0.157 | 0.004 | 0.409 | 0.349 |
| Jury | 6 | 4 | 0.159 | 0.002 | 0.127 | 0.016 | 0.098 | 0.327 |
| Public | 6 | 4 | 0.261 | −0.001 | 0.176 | 0.004 | 0.402 | 0.346 |
| Jury | 7 | 3 | 0.083 | −0.005 | 0.116 | 0.154 | 0.081 | 0.296 |
| Public | 7 | 3 | 0.243 | 0.001 | 0.202 | 0.014 | 0.424 | 0.336 |
| Jury | 8 | 2 | 0.173 | −0.001 | 0.134 | 0.016 | 0.178 | 0.337 |
| Public | 8 | 2 | 0.387 | −0.004 | 0.271 | 0.004 | 0.440 | 0.415 |
| Jury | 9 | 1 | 0.210 | 0.001 | 0.220 | 0.056 | 0.137 | 0.329 |
| Public | 9 | 1 | 0.322 | 0.006 | 0.335 | 0.042 | 0.375 | 0.349 |

- **Il televoto è più stabile delle giurie su tutti e tre gli indicatori chiave.** Al lag 1:
  - Spearman: public 0.263 vs jury 0.099, differenza +0.165, 9/9 coppie, p = 0.0039 (Holm 0.0117)
  - Residual Pearson: public 0.471 vs jury 0.118, differenza +0.353, 9/9, p = 0.0039 (Holm 0.0117)
  - Jaccard: public 0.359 vs jury 0.292, differenza +0.067, 8/9, p = 0.0117 (Holm 0.0117)
- La stabilità **non decade** in modo monotono: la residual Pearson resta tra 0.07 e 0.18 per le giurie e tra 0.38 e 0.47 per il televoto a tutti i lag, e sulla residual Pearson entrambi i layer sono significativi in **tutti e 9 i lag**. La Spearman grezza è più rumorosa: significativa in 7/9 lag per le giurie (lag 7, p = 0.154, e lag 9, p = 0.056) e in 9/9 per il televoto.
- Al lag 1 le diadi comuni vanno da 496 (2025–2026) a 741 (2016–2017), con media 680; per i lag da 2 a 9 la media scende a 549–622. La dimensione campionaria effettiva è comunque limitata dalla struttura delle eleggibilità.

## Limitazioni

- **QAP con zeri strutturali.** La permutazione cambia l'insieme delle diadi comuni oltre all'accoppiamento, il che è il nullo corretto per reti con zeri strutturali, ma rende la distribuzione nulla dipendente dalla geometria delle maschere.
- **Effetti residui.** La residualizzazione rimuove gli effetti di livello votante e destinatario in modo lineare (due-vie centering). Interazioni non lineari o effetti di ordine superiore non sono catturati.
- **Esclusione del WLD.** Dal 2023 metà del voto pubblico è *Rest of the World*; escludere il WLD lascia la metà nazionale. La stabilità del layer public è quindi misurata sulla parte collegata ai paesi, e le conclusioni valgono per quella parte.
- **Allineamento sui paesi comuni.** Nel confronto temporale si allineano solo i paesi presenti in entrambe le edizioni. Paesi che entrano/escono dall'insieme dei finalisti non contribuiscono alla stabilità; questo è corretto per la domanda posta ma riduce il campione ai lag maggiori.
- **Coppie consecutive non indipendenti.** Il confronto jury vs public al lag 1 usa 9 coppie di edizioni, ma ogni edizione intermedia compare in due coppie, quindi le 9 differenze non sono indipendenti e il p del sign-flip è un po' ottimista. Il risultato resta netto (9/9 coppie per Spearman e residual Pearson).
- **Nessuna inferenza causale.** La stabilità osservata è descrittiva: non dice *perché* il pattern persiste (geografia, cultura, qualità della canzone, inerzia del voto).

## Output

`results/rq4/`:

- `rq4_layer_similarity.csv`: per edizione, celle comuni, entrambe > 0, le 4 statistiche + null mean, q025, q975, p-value QAP, più `spearman_both_positive`.
- `rq4_temporal_stability.csv`: per layer, lag, statistica, coppie, media osservata, null mean, q025, q975, p-value.
- `rq4_temporal_pairs.csv`: per layer, lag, year_a, year_b, celle comuni, le 4 statistiche per ogni coppia di edizioni.
- `rq4_temporal_layer_diff.csv`: confronto jury vs public al lag 1 (paired sign-flip test su 9 coppie), con p exact, Holm, FDR.

`figures/rq4/`:

- `rq4_layer_similarity.png`: tre pannelli — Spearman e residual Pearson per anno con bande QAP; Jaccard per anno con banda QAP; mappa di calore log-counts jury vs public per l'ultima edizione (2026).
- `rq4_temporal_stability.png`: tre pannelli — Spearman per lag per layer con bande QAP; residual Pearson per lag per layer con bande QAP; due heatmap Spearman tra tutte le coppie di edizioni (jury a sinistra, public a destra).

## Riproduzione

Requisiti: Python con `numpy`, `matplotlib` (nessuna dipendenza pesante, niente scipy).

```bash
cd RQ4
python src/analyze_rq4_layer_similarity.py      # ~5 secondi
python src/analyze_rq4_temporal_stability.py    # ~18 secondi
```

Gli script non hanno opzioni da riga di comando: seed, numero di permutazioni e lag massimo sono costanti in cima al file (`SEED`, `N_PERM`, `MAX_LAG`). Entrambi arrotondano i CSV a 10 decimali e sono **byte-identici** su esecuzioni consecutive.