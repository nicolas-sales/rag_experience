# RAG sur PDF

Assistant qui répond à des questions sur un PDF et montre la page et la zone d'où vient la réponse.

Le PDF est converti en Markdown en gardant la position des textes, tableaux et images, avec
**1 chunk par page**. Les pages sont indexées dans Qdrant, puis une app Streamlit pose les
questions au LLM et surligne la source dans le PDF.

Contraintes du projet : **CPU uniquement**, solution **généraliste** (pas de réglage pour un PDF
précis) et basée sur **PyMuPDF**.

## Versions

| Dossier | Contenu |
| --- | --- |
| `src/` | version d'origine : blocs PyMuPDF, CLIP + DePlot pour les graphiques |
| `src2/` | + ordre de lecture des blocs (`layout.py`, modèle de layout de pymupdf4llm) |
| `src3/` | + OCR des graphiques et des logos (EasyOCR), **sans DePlot**. Version recommandée |

## Ingestion (`src3/ingestion.py`)

L'objectif est que chaque chunk soit cohérent : le texte dans le bon ordre, avec les tableaux
et le contenu des images à leur place.

**1. Texte : PyMuPDF**
- Le texte est lu caractère par caractère (`get_text("rawdict")`) avec sa position.
- Le texte invisible (`alpha == 0`), présent en double dans les PDF issus de PowerPoint, est ignoré.
- PyMuPDF ajoutait des espaces dans les titres à lettres espacées (« Le m ot du CEO »). On
  n'ajoute plus un espace que si l'écart entre deux lettres dépasse 0,2 × la taille de police.
- Les lignes sur la même rangée sont fusionnées.

**2. Zones de la page : pymupdf4llm**
- Le modèle de layout de `pymupdf4llm` (pymupdf-layout) découpe la page en zones : titre,
  sous-titre, liste, image, tableau…
- Les lignes de texte sont regroupées en blocs selon leur zone ; les titres deviennent `##`,
  les éléments de liste `- `.
- Les en-têtes répétés sur au moins 3 pages (menus) sont retirés.

**3. Tableaux : PyMuPDF**
- `find_tables(use_layout=False)` : il faut désactiver le layout, sinon le modèle de
  pymupdf4llm fait planter la détection.
- Les lignes de texte déjà présentes dans un tableau sont retirées pour éviter les doublons.

**4. Ordre de lecture : XY-cut**
- La page est coupée récursivement le long des plus grands espaces vides, horizontaux puis
  verticaux, ce qui donne l'ordre colonne par colonne.
- Tout ce qui se trouve sur une même image (graphique annoté, infographie) reste groupé.

**5. Images : CLIP + EasyOCR**
- **CLIP** classe chaque image : graphique, infographie, logo, photo, schéma…
- **EasyOCR** (CPU, 300 dpi) lit les graphiques et les logos :
  - chaque texte lu a sa position (bbox) ;
  - chaque nombre est associé au texte juste en dessous, par exemple l'année sous la barre :
    `2023 : 936` ;
  - pour un logo, on garde le nom lu (`Logo : framatome`), sauf s'il apparaît sur au moins
    3 pages (logo de l'entreprise).
- **DePlot**, utilisé dans `src` et `src2`, a été retiré de `src3` : il devine des valeurs à
  partir du dessin et en invente (« Networks : 9,8 % », un chiffre absent du PDF).
- Les résultats de CLIP et de l'OCR sont mis en cache : une nouvelle ingestion est rapide.

**6. Sorties** (`data/processed/src3/`)
- `chunks.json` : 1 chunk par page, indexé dans Qdrant ;
- `pages_markdown.md` : toutes les pages en Markdown, pour relire ce que voit le LLM ;
- `source_elements_v3.json` : les éléments de chaque page avec leur bbox, pour surligner la source ;
- `blocks_diagnostic.md` : le détail de chaque bloc (type, position, traitement).

## RAG

- Embeddings `text-embedding-ada-002`, base Qdrant locale, 4 pages retrouvées par question.
- Le LLM (`gpt-5-mini`) reçoit le Markdown des pages et la liste de leurs éléments.
- Il renvoie la réponse et les éléments utilisés, que l'app surligne dans le PDF.

## Installation et utilisation

Deux environnements Python, car RAGAS 0.2.15 n'est pas compatible avec les versions du pipeline :
- `venvrag` : pipeline et app (`requirements.txt`) ;
- `venveval` : évaluation RAGAS (`evaluation/requirements.txt`).

Mettre la clé OpenAI dans `.env` : `OPENAI_API_KEY=sk-...`

Depuis la racine du projet :

```
venvrag\python.exe -m src3.ingestion     # PDF -> Markdown (data/processed/src3/)
venvrag\python.exe -m src3.indexing      # Markdown -> Qdrant (data/qdrant_db_src3)
streamlit run app/app_src3.py            # application
```

Le PDF traité est `data/raw/Plan_stratégique_Impact.pdf` (83 pages).

## Évaluation avec RAGAS

```
venvrag\python.exe -m evaluation.run_evaluation_src3     # 1. le RAG répond aux questions
venveval\python.exe -m evaluation.evaluate_ragas_src3    # 2. RAGAS note les réponses
venveval\python.exe -m evaluation.analyze_results_src3   # 3. résumé
```

Les mêmes informations sont demandées de trois façons (constante `DATASET_NAME` dans les 3 scripts) :

| Dataset | Style de question | Exemple |
| --- | --- | --- |
| `dataset` | phrases complètes | « Quelle note Davidson a-t-elle obtenue à l'évaluation EcoVadis 2025 ? » |
| `dataset_mots_pdf` | reprend les mots du PDF | « Quelle est la note EcoVadis 2025 de Davidson ? » |
| `dataset_simple` | questions courtes, comme dans l'app | « Note EcoVadis 2025 ? » |

Les questions couvrent le texte, les tableaux, les chiffres lus dans les graphiques et une
question dont la réponse n'est pas dans le document (le RAG doit le dire).

### Métriques

Chaque note va de 0 à 1. Un LLM juge (`gpt-4o-mini`) compare la question, les pages
retrouvées, la réponse du RAG et la réponse de référence.

| Métrique | Question posée par le juge | Ce qu'elle évalue |
| --- | --- | --- |
| faithfulness | Chaque affirmation de la réponse est-elle écrite dans les pages retrouvées ? | le LLM n'invente pas |
| answer_relevancy | La réponse répond-elle à la question ? | le LLM ne répond pas à côté |
| context_precision | Les pages retrouvées sont-elles utiles, et les bonnes en tête ? | la recherche Qdrant |
| context_recall | Les pages retrouvées contiennent-elles toute la réponse de référence ? | la recherche Qdrant |
| answer_correctness | La réponse dit-elle la même chose que la référence ? | tout le RAG |

### Résultats (`src3`, 33 questions communes)

| Métrique | `dataset` | `dataset_mots_pdf` | `dataset_simple` |
| --- | --- | --- | --- |
| faithfulness | 0,80 | 0,85 | 0,89 |
| answer_relevancy | 0,80 | 0,86 | 0,88 |
| context_precision | 0,75 | 0,90 | 0,85 |
| context_recall | 0,91 | 0,96 | 0,97 |
| answer_correctness | 0,79 | 0,82 | 0,83 |

Ce qu'on en retient :
- **L'extraction fonctionne.** Quand la bonne page est retrouvée, la réponse est presque toujours
  juste, y compris pour les chiffres lus dans les graphiques (936 tCO2e, 6 476 tCO2e).
- **Retirer DePlot** a supprimé les chiffres inventés.
- **Retirer la citation de page du prompt** a fait gagner +0,1 à +0,2 en faithfulness : le juge
  ne pouvait pas vérifier « page 14 », absent du texte des pages.
- **La limite principale est la recherche Qdrant** :
  - les questions longues trouvent moins bien la bonne page que les questions courtes ;
  - les pages qui mélangent plusieurs sujets sont mal retrouvées ;
  - un chiffre proche sur une autre page peut tromper le LLM (EcoVadis : 79/100 au lieu de 74/100).

Limites des métriques :
- les réponses « l'information n'est pas dans le document », même justes, sont mal notées ;
- les réponses courtes et justes peuvent être sous-notées, car un détail en plus compte comme une erreur ;
- chaque évaluation n'a été lancée qu'une fois, et le LLM varie d'un essai à l'autre.

### Défauts connus de l'extraction
- Quelques espaces restent dans les titres très espacés (« IMP ACT SOC IAL »).
- Dans certains graphiques, l'association nombre ↔ année est fausse (page 25, page 45 avec deux axes).
