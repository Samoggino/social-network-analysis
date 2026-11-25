# RQ4 · Accordo fra giurie e televoto e stabilità temporale

La RQ4 chiede quanto si assomiglino i voti delle giurie e del televoto nazionale nella stessa finale e quanto ciascun sistema mantenga la propria struttura di voto fra finali consecutive. I lag superiori a uno descrivono confronti a distanza maggiore.

## Dati e confronti

- Dieci Grand Final dal 2016 al 2026. Il 2020, anno senza concorso, è assente. I lag contano le edizioni e il passaggio 2019–2021 vale uno.
- Le 20 matrici annuali provengono da `../RQ1/processed_data/matrices/`. La RQ4 usa le matrici, indipendentemente dai risultati delle altre domande. Un valore vuoto indica un voto inammissibile. Lo zero indica una diade ammissibile che non ha ricevuto punti.
- Il voto *Rest of the World* (`WLD`) è escluso per confrontare i due sistemi sui votanti nazionali. Dal 2023 vale un set aggiuntivo da 58 punti. [Regolamento Eurovision](https://www.eurovision.com/newsroom/rules-of-the-contest/)
- Una diade è una coppia diretta votante–destinatario. I confronti usano l'intersezione delle diadi ammissibili. Nel tempo si allineano prima i Paesi comuni e si confrontano giurie e televoto sulle stesse celle per ogni coppia di edizioni.

## Statistiche e test

**Metrica primaria.** Per ciascuna delle due reti confrontate si stimano, per minimi quadrati sulle sole celle comuni, intercetta ed effetti fissi additivi di votante e di destinatario. Il Pearson dei due vettori di residui misura l'accordo dopo questo aggiustamento. Il codice costruisce con una SVD una base ortonormale del disegno, che include l'intercetta, e riusa la proiezione quando la maschera rimane fissa. La stima preserva gli zeri ammissibili e lascia fuori le celle inammissibili. La metrica è indefinita se uno dei vettori di residui non ha variabilità.

**Metriche complementari.** Spearman con ranghi medi e Pearson grezzo usano tutte le diadi comuni. Jaccard misura la quota di diadi premiate da entrambi fra quelle premiate da almeno uno. Nella stessa edizione si riporta anche Spearman sulle diadi premiate da entrambi, un sottoinsieme selezionato dai punteggi stessi.

**QAP nella stessa finale.** Si permutano insieme righe e colonne del televoto entro i due gruppi di Paesi, finalisti e non finalisti. La giuria rimane fissa. Si verifica a ogni replica che l'eleggibilità resti identica, cella per cella. La permutazione conserva ciascuna scheda come insieme di punti e il profilo dei punti ricevuti dai finalisti a meno dell'etichetta. Il test valuta l'accordo con le identità osservate rispetto a questo riferimento condizionato al ruolo.

**QAP temporale congiunto.** Ogni replica estrae una permutazione per finale, indipendentemente fra finali, con gli stessi vincoli e controlli. Si usa la stessa permutazione per giurie e televoto di quella finale e la si riutilizza in tutte le coppie che la comprendono. Il nullo conserva la struttura congiunta annuale dei voti e tiene conto delle edizioni condivise fra coppie. Conservando ciascuna maschera annuale, conserva anche la sua intersezione con ogni altra maschera. La statistica di ogni layer è la media a pesi uguali sulle nove coppie consecutive. Per il divario si sottraggono le due medie **nella stessa replica**. Il nullo ipotizza che, dati vincoli e schede annuali, le etichette dei Paesi siano scambiabili entro ruolo e indipendentemente per edizione. Il test del divario valuta la compatibilità con questo riferimento. L'uguaglianza della stabilità fra due processi che possono entrambi essere persistenti è un'ipotesi diversa.

**Code e correzioni.** Per entrambi i nulli si usano 9.999 repliche e p-value bilaterali calcolati come il doppio della coda empirica minore, troncato a uno. In ciascuna coda si aggiunge uno al conteggio e al denominatore. Il minimo p grezzo è 0,0002. Holm è applicata separatamente alla famiglia dei dieci confronti nella stessa edizione e a quella dei tre test temporali al lag 1 (giurie, televoto, divario). Gli altri indicatori, i lag 2–9 e i controlli di robustezza sono descrittivi. I quantili 2,5% e 97,5% descrivono le simulazioni del nullo.

**Robustezza.** Si ripete il confronto al lag 1 sulle sole diadi ammissibili in tutte le edizioni. Si ricalcola inoltre la media escludendo ogni finale a turno e rimuovendo tutte le coppie che la coinvolgono. La procedura non crea nuovi abbinamenti. Queste analisi misurano la sensibilità al campione di diadi e alle singole edizioni.

## Risultati

### Accordo nella stessa edizione

Su dieci finali, il Pearson dei residui va da **0,167 a 0,313** e ha media **0,2413**. Tutti e dieci i confronti annuali hanno **p grezzo = 0,0002** e **p Holm = 0,0020** sotto il QAP entro ruolo. Il valore grezzo raggiunge il limite di risoluzione Monte Carlo. Su tutte le diadi, Spearman, Pearson grezzo e Jaccard medi sono rispettivamente **0,311**, **0,329** e **0,384**. Sulle diadi premiate da entrambi, lo Spearman medio è **0,191**.

### Stabilità tra edizioni consecutive

| Statistica | Giurie | Televoto | Differenza | Coppie con televoto più alto |
|---|---:|---:|---:|---:|
| Pearson dei residui | 0,1178 | 0,4717 | +0,3539 | 9/9 |
| Spearman | 0,0989 | 0,2634 | +0,1646 | 9/9 |
| Pearson grezzo | 0,1141 | 0,3187 | +0,2045 | 9/9 |
| Jaccard | 0,2918 | 0,3590 | +0,0672 | 8/9 |

Le due medie residue e il divario sono superiori a quanto atteso sotto il riferimento di scambiabilità delle identità fra edizioni (**p grezzo = 0,0002 e p Holm = 0,0006** per ciascuno dei tre test). Per il divario, i quantili centrali del nullo vanno da **−0,0362 a +0,0366**. Il risultato di **+0,3539** documenta un vantaggio del televoto nelle finali analizzate ed è incompatibile con questo nullo. I lag da 2 a 9 hanno da otto a una coppia e le loro curve descrivono l'andamento osservato senza un test di decadimento.

### Robustezza

Sulle **130 diadi sempre ammissibili**, tra **27 votanti** e **5 destinatari**, il divario del Pearson residuo è **+0,3464** e il televoto resta più alto in **9 coppie su 9**. Per Jaccard il divario scende invece a **+0,0074** e il televoto prevale in **5 coppie su 9**. Escludendo una finale alla volta, il divario del Pearson residuo resta fra **+0,3182 e +0,3743**, su sette o otto coppie. La robustezza riguarda soprattutto la concordanza dei punteggi dopo l'aggiustamento additivo. La sovrapposizione delle sole diadi positive è più sensibile alla composizione dei finalisti.

## Limiti

Il QAP controlla il ruolo e l'eleggibilità. La scambiabilità delle etichette è un'assunzione del modello: il riferimento non fissa la popolarità di ciascun Paese né le affinità geografiche. Gli effetti fissi assorbono i livelli additivi di chi vota e chi riceve punti sulle celle confrontate. Interazioni e altre strutture del voto possono contribuire ai residui. Il sottoinsieme di diadi sempre ammissibili privilegia Paesi presenti e finalisti con continuità. L'analisi riguarda le finali osservate e non attribuisce cause alle regolarità del voto.

## Riproduzione e file

Dalla cartella `RQ4`, con Python 3.12 nell'ambiente di riferimento:

```bash
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B run_all.py
```

Per usare matrici in un'altra posizione, aggiungere `--matrices "percorso/alle/matrici"`. L'opzione `--output-dir` cambia la radice degli output. I default sono 9.999 permutazioni e semi 42 per l'analisi annuale e 43 per quella temporale. In `run_all.py`, `--seed` imposta il primo seme e il secondo è quello successivo. Gli script originari restano eseguibili anche singolarmente e accettano gli stessi parametri, con il rispettivo seme predefinito. Usare `run_all.py` per generare anche il registro completo.

| File in `results/rq4/` | Contenuto |
|---|---|
| `rq4_layer_similarity.csv` | Accordo per edizione e test primario annuale |
| `rq4_temporal_pairs.csv` | Statistiche osservate e copertura per coppia e layer |
| `rq4_temporal_stability.csv` | Medie per lag e test primari al lag 1 |
| `rq4_temporal_layer_diff.csv` | Divario osservato al lag 1 e test del divario sotto il nullo congiunto |
| `rq4_robustness.csv` | Diadi fisse ed esclusione di ogni finale, con copertura e variazione rispetto alla stima principale |
| `rq4_run_config.json` | Versioni, semi, repliche, famiglie di test e SHA-256 delle 20 matrici |

Le celle inferenziali vuote nei CSV corrispondono a statistiche descrittive. Le figure in `figures/rq4/` mostrano l'accordo annuale e l'andamento per lag, con scale che rappresentano anche le correlazioni negative fra edizioni.
