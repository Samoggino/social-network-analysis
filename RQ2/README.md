# RQ2 — Eurovision voting communities and homophily

Versione rivista della RQ2. Comprende dati, sorgenti, risultati e grafici per le finali 2016–2026, escluso il 2020, con giurie e televoto separati. RQ3 legge direttamente le matrici, gli attributi e le etichette delle comunità da questa cartella.

## Cosa contiene

- `src/validate_data.py`: controllo di integrità dei 20 grafi e delle regole delle schede.
- `src/make_country_attributes.py`: classificazione dei 45 Paesi per sottoregione UN M49, famiglie linguistiche e **blocchi Eurovision esplorativi**.
- `src/build_eurovision_data.py`: ricostruzione *facoltativa* delle matrici dai file sorgente EurovisionAPI, non inclusi; le matrici necessarie sono **già fornite** in `processed_data/matrices/`.
- `src/analyze_rq2.py`: descrittive, Louvain, assortatività e quote di punti.
- `src/analyze_rq2_opportunity.py`: opportunità eleggibili, omofilia, margini e permutazioni delle etichette.
- `src/analyze_rq2_partitions.py`: NMI/ARI, benchmark delle etichette, stabilità Louvain.
- `src/analyze_rq2_consensus.py`: consenso di 200 Louvain, test e appartenenze dei Paesi.
- `src/analyze_rq2_language_within.py`: omofilia linguistica fra sottoregioni differenti, con benchmark **distinti** per scelte e punti.
- `src/analyze_rq2_modularity_null.py`: modello nullo per modularità che permuta i pesi sull'insieme fisso degli archi.
- `src/analyze_rq2_ballot_null.py`: **nuovo controllo** per la modularità con schede casuali valide (10 destinatari eleggibili distinti, punteggi 1–8, 10, 12).
- `src/analyze_rq2_robustness.py`: sensibilità delle principali differenze giuria–televoto escludendo un'edizione alla volta.
- `results/rq2/`, `figures/rq2/`: output **rigenerati** in questa copia.

## Esecuzione

Da PowerShell, partire dalla radice del repository.

```powershell
cd RQ2
py -m pip install -r requirements.txt
py run_all.py
```

L'ambiente di riferimento è Python 3.13.12 con le versioni in `requirements.txt`. In questo ambiente sono stati verificati i CSV del consenso, comprese le appartenenze e la firmness. In una riesecuzione con Python 3.12 e NetworkX 3.7 le appartenenze coincidono e alcuni diagnostici di stabilità cambiano. Con 2.000 repliche, i p-value annuali dei due nulli differiscono al massimo di due incrementi Monte Carlo (2/2.001). Le combinazioni selezionate dopo Holm e i p-value Holm dei confronti appaiati coincidono. I CSV pubblicati conservano i valori dell'ambiente di riferimento.

Non sono necessari i dati grezzi EurovisionAPI per riprodurre le analisi: le 20 matrici sono già presenti. Le analisi più lente sono Louvain ripetuto e i modelli nulli.

Per ricostruire *anche* le matrici dalla fonte grezza, utilizzare `python src/build_eurovision_data.py <cartella dataset-main/data/senior>`, poi rieseguire `python src/validate_data.py` e l'intera pipeline. **La ricostruzione dai JSON grezzi non è stata verificata qui**, dato che tali JSON non erano disponibili.

## Modifiche principali rispetto agli script forniti

1. Corretto il conteggio stampato delle **opportunità**: 19.698 nei due livelli complessivi, non il doppio; i non finalisti non subiscono la sottrazione di un'autovotazione.
2. Integrata la correzione già adottata dai colleghi per la **ponderazione delle scelte linguistiche cross-region**.
3. Corretta **anche la ponderazione del benchmark dei punti cross-region**: si pesano le probabilità individuali per il totale di punti interregionali, non per il numero di scelte.
4. Aggiunti benchmark separati per giurie e televoto nei **due pannelli del grafico linguistico**; aggiornato il test annuale dell'eccesso rispetto al benchmark appropriato per ciascuna statistica.
5. Salvate le **assegnazioni consensuali** dei Paesi (`rq2_consensus_labels.csv`), come nell'aggiornamento Git del gruppo.
6. Rese più coerenti le famiglie linguistiche per **Finlandia, Irlanda, Cipro e Malta**, considerando le famiglie delle lingue ufficiali (senza introdurre le lingue delle canzoni); Malta non è classificata come Romance solo perché mediterranea. **ATTENZIONE:** questo cambia i risultati rispetto al dataset iniziale. Non considerare le percentuali direttamente comparabili senza un'analisi di sensibilità.
7. Rimossa la categoria **Big Five** dalla variabile *esplorativa* `eurovision_block`, riassegnando i cinque Paesi a gruppi euristici. Questa variabile non costituisce una misura scientificamente validata di cultura; gli indici che la usano restano **esplorativi**.
8. Aggiunto un **secondo modello nullo** che conserva le regole delle schede Eurovision; il vecchio modello nullo è mantenuto per confronto.
9. Aggiunta sensibilità **leave-one-edition-out**.
10. Ridotti i campioni casuali di coppie Louvain per la metrica di stabilità da 2.000 a **240** (numero di seed invariato a 100): ciò riduce il tempo e introduce maggiore errore Monte Carlo. Il consenso mantiene 200 seed e i benchmark delle partizioni 500 permutazioni.

## Parametri e accuratezza Monte Carlo

Entrambi i modelli nulli di modularità usano **2.000 repliche per rete e ambito**. Il minimo p-value Monte Carlo è 1/2.001 (circa 0,00050). I CSV annuali riportano i p-value nominali a coda superiore. Ricalcolando Holm separatamente sulle 40 combinazioni di anno, livello e ambito di ciascun modello, risultano 5 casi sotto 0,05 per le schede casuali e 1 per i pesi permutati. I p-value dei confronti appaiati tra giurie e televoto sono riportati nei rispettivi CSV. La [relazione PDF](Spiegazione_analisi_e_risultati.pdf) conserva anche il contesto dello ZIP preliminare. I CSV di questa cartella contengono le elaborazioni a 2.000 repliche.

## Limiti statistici importanti

- Le reti della RQ2 vengono rese non orientate sommando i due versi: le **comunità risultanti non dimostrano reciprocità**, che è studiata separatamente dalla RQ1.
- Il null `modularity_null` **mantiene la topologia e permuta i pesi**. Il null `ballot_null` **mantiene eleggibilità e schede** ma non i gradi/strength empirici. Sono due ipotesi diverse; **non sostituire il secondo al primo come se uno fosse sempre più corretto**.
- L'omofilia linguistica delle coppie di sottoregioni diverse è una **associazione condizionata**, non prova un effetto causale della lingua né elimina tutta la prossimità geografica.
- La verifica dell'eccesso con *sign-flip* dipende dall'ipotesi di simmetria/scambiabilità delle differenze annuali. La sensibilità leave-one-year-out **non rende indipendenti le edizioni**.
- La classificazione delle famiglie delle lingue **ufficiali** non equivale alla lingua realmente cantata e non riflette automaticamente l'intelligibilità o l'affinità culturale.
- NMI/ARI con un singolo gruppo linguistico primario in `analyze_rq2_partitions.py` usa **una sola etichetta per Paese** (prima famiglia nell'elenco). Gli script sull'omofilia usano invece l'intersezione di **tutte** le famiglie codificate. Le due operazionalizzazioni misurano concetti diversi.
- `eurovision_block` è una classificazione euristica, non una partizione culturale indipendente validata. Non usatela per conclusioni culturali forti.
- Correzioni Holm/BH sono applicate **per famiglie di test nei singoli script**, non all'intera raccolta di ipotesi esplorative.
- Gli output originali del gruppo non sono stati sovrascritti, e i risultati qui sono **nuovi**, non una replica byte-identica dei risultati precedenti.

## Provenienza e verifica

Sorgenti iniziali: gli otto script `.py` della RQ2 condivisi nella conversazione, con integrazione manuale delle modifiche al test linguistico introdotte nel commit Git `015d93c` (18 novembre 2026). **Non è un clone automatico dell'intero commit**. Le matrici sono state estratte dall'archivio del progetto `Eurovision_SNA_matrici_e_dataset.zip` fornito in conversazione. Sono state confrontate per integrità con gli stessi vincoli strutturali dichiarati nella RQ2.

Validazione eseguita su tutte le matrici: 20 reti, 45 Paesi, 393 votanti-edizione, **7.860 archi positivi** e **19.698 opportunità**. Sono state eseguite tutte le analisi ed esportati CSV e figure allegati, usando le impostazioni di campionamento qui descritte.
