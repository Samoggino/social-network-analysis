# RQ3 - Spiegazione delle analisi e dei risultati

**Eurovision Song Contest.** Finali dal 2016 al 2026, escluso il 2020. Revisione della documentazione del 25 novembre 2026.

## 1. Domanda di ricerca e dati

La RQ3 studia quali finalisti ricevono più punti, quanto il sostegno si concentra su pochi Paesi e in che misura proviene dal gruppo geografico o culturale del destinatario. Le 20 reti dirette e pesate rappresentano giurie e televoto nelle dieci edizioni. Un arco va dal Paese che assegna i punti al finalista che li riceve, con l'autovoto escluso.

Gli script leggono direttamente matrici, attributi e comunità dalla cartella della **RQ2 rivista**. Le matrici coincidono con quelle della RQ1. Dal 2023 il Rest of the World (`WLD`) assegna un set aggiuntivo di 58 punti, equivalente al televoto di un Paese partecipante. L'analisi del televoto considera le sole schede nazionali. [Regole di voto Eurovision](https://www.eurovision.com/newsroom/rules-of-the-contest/)

## 2. Prestigio e classifiche

L'**in-degree** conta i Paesi che hanno assegnato almeno un punto. L'**in-strength** somma i punti ricevuti. I punti per opportunità dividono il totale per il numero di votanti ammissibili. PageRank e HITS authority sono vicini alla classifica per in-strength, con correlazioni medie di Spearman di circa **0,937** e **0,995**.

Fra i 33 Paesi con almeno quattro finali, i primi cinque delle giurie sono Svizzera, Svezia, Bulgaria, Australia e Italia. Nel televoto sono Ucraina, Bulgaria, Italia, Israele e Moldavia. La correlazione dei ranghi fra le due classifiche è **0,27**.

## 3. Concentrazione del consenso

Il **Gini medio** è **0,447 per le giurie** e **0,538 per il televoto**. La quota di punti dei primi tre sale dal **31,5% al 37,2%**. Entrambe le misure sono più alte nel televoto in tutte le edizioni, con **p Holm = 0,0234** nei test appaiati sui valori osservati.

L'entropia di Shannon è divisa per il logaritmo del numero di finalisti, inclusi i finalisti a zero punti (19 casi nel dataset). La media è **0,895 nelle giurie** e **0,844 nel televoto**, con un riferimento di **0,990** sotto le schede uniformi. Il p-value bilaterale annuale è circa 0,00050 in tutte le 20 reti, a livello nominale. Entropia e indice di Herfindahl possono ordinare diversamente le distribuzioni.

## 4. Sostegno geografico

L'**home excess** sottrae dalla quota di punti ricevuti dal proprio gruppo la quota di votanti ammissibili di quel gruppo. La media per sottoregione è **0,083 nelle giurie** e **0,193 nel televoto**. Il divario è di 11,0 punti percentuali (p Holm = 0,0234 sui valori osservati). Il **participation ratio** rapporta la dispersione dei punti tra gruppi a quella dei votanti ammissibili. Per le sottoregioni vale in media **0,835** e **0,727**. Le due misure di sostegno usano i finalisti con punti ricevuti.

## 5. Modelli nulli

**Schede uniformi.** Le 2.000 simulazioni per rete assegnano a ogni votante i dieci punteggi regolamentari (da 1 a 8, 10 e 12) su dieci finalisti distinti scelti fra quelli ammissibili. Ogni scheda conserva l'eleggibilità e i suoi punteggi. Il numero di votanti e i punti ricevuti da ciascun finalista variano per effetto del sorteggio. Lo stesso tipo di modello fornisce il riferimento per l'entropia.

**Popolarità del destinatario fissata.** Nelle 1.000 simulazioni per rete, ciascun finalista mantiene il numero di votanti, il totale dei punti e la distribuzione dei punteggi ricevuti. L'identità dei votanti è riassegnata fra quelli ammissibili, indipendentemente per ogni finalista. Il numero di voti in uscita, il totale dei punti assegnati e i punteggi di una scheda individuale possono variare. La concentrazione dei punti ricevuti è fissa per costruzione, quindi questo modello valuta la provenienza del sostegno.

## 6. Come leggere i p-value

I **test Monte Carlo annuali** riportano `p_high` per la coda superiore e `p_low` per la coda inferiore. `p_two_sided` usa entrambe le code e confronta le distanze dalla media del nullo simulato. Il calcolo aggiunge uno al conteggio delle repliche estreme e uno al totale delle repliche valide. I p-value annuali sono nominali, senza correzione per confronti multipli. I conteggi sotto 0,05 sono descrittivi.

I **confronti appaiati** sono bilaterali. Il test esatto confronta il valore assoluto della differenza media fra televoto e giurie con quelli ottenuti dalle 1.024 combinazioni di segno delle dieci differenze annuali. Un CSV applica il test ai valori osservati. L'altro lo applica agli z-score rispetto al nullo a popolarità fissata. In ciascuna famiglia di 12 statistiche, `p_exact` è il p-value grezzo, `p_holm` è corretto con Holm e `p_fdr` è corretto con Benjamini-Hochberg. Le conclusioni sui confronti appaiati usano Holm.

## 7. Home excess a popolarità fissata

Gli z-score geografici medi sono **2,87 per le giurie** e **5,89 per il televoto**. Il confronto appaiato dà **p esatto = 0,0039** e **p Holm = 0,0391**. Per i blocchi culturali, p Holm = 0,0234.

Nei test annuali sull'home excess geografico, la **coda superiore** dà p nominale sotto 0,05 in **8/10** reti delle giurie e **10/10** del televoto. Il test **bilaterale** dà **7/10** e **10/10**, rispettivamente.

## 8. Prestigio e partecipazione a popolarità fissata

Il codice originale usava le posizioni dei finalisti selezionati per indicizzare il vettore di tutti i Paesi. Il disallineamento interessava tutte le 20 reti. Entrambe le revisioni riallineano il prestigio al finalista corretto. L'integrazione usa gli stessi finalisti nei valori osservati e simulati, anche nel sottoinsieme con almeno cinque votanti.

| Spearman geografica media su dieci edizioni | Giurie | Televoto |
| --- | ---: | ---: |
| Osservata | 0,717 | 0,815 |
| Nullo con schede uniformi | 0,251 | 0,253 |
| Nullo corretto a popolarità fissata | 0,753 | 0,836 |

I coefficienti osservati sono positivi e le loro medie sono inferiori al riferimento a popolarità fissata. In entrambi i livelli, nessun p-value annuale della coda superiore è sotto 0,05 con questo nullo. I dati mostrano quindi un'associazione descrittiva compatibile con il riferimento corretto. Il confronto bilaterale appaiato degli z-score della correlazione dà **p esatto = 0,8125** e **p Holm = 1,0**.

Sui blocchi culturali aggiornati, lo z-score medio della correlazione è +0,467 per le giurie e -1,019 per il televoto. Il confronto appaiato dà p Holm = 0,0391. Il risultato riguarda la distanza standardizzata dal riferimento di ciascun livello.

## 9. Sensibilità e limiti

Con almeno cinque votanti per finalista, il confronto degli z-score dell'home excess geografico dà p Holm = 0,0410. Per il participation ratio geografico, il p Holm è 0,0938 sul campione completo e 0,0234 nel sottoinsieme.

Le comunità RQ2 derivano dagli stessi voti analizzati, quindi i confronti che le usano sono descrittivi. I test appaiati dipendono dall'assunzione di scambiabilità dei segni sotto l'ipotesi nulla. Le edizioni possono essere dipendenti e i risultati sono esplorativi. La randomizzazione lascia fuori fattori come la diaspora, la lingua e la qualità percepita. La causalità geografica resta indeterminata.

## 10. Come riprodurre i risultati

Dalla radice del repository, entrare in RQ3 ed eseguire i comandi nell'ordine indicato. Gli input provengono da RQ2.

```bash
cd RQ3
python -m pip install -r requirements.txt
python src/analyze_rq3.py
python src/analyze_rq3_popularity_null.py
python src/analyze_rq3_ranking.py
```

I due script di simulazione usano il seme 2026 con le numerosità indicate sopra. La classifica usa l'aggregato prodotto dal primo script. I comandi riscrivono i risultati in `results/rq3/` e i grafici in `figures/rq3/` di RQ3.
