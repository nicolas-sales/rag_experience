# Explication de la solution : `comparaison_extraction4.py`

Ce document explique, fonction par fonction, comment le script transforme une page PDF en Markdown pour le RAG en respectant la position des éléments (textes, images, tableaux).

Tous les exemples viennent de la **page 24 de `Plan_stratégique_Impact.pdf`** (la page « Égalité femmes-hommes » : un texte à gauche, un tableau sans bordures à droite, un menu en haut).

---

## 0. Pourquoi une v4 ?

Sur les pages 16 et 24, la v3 ne sortait presque rien. Trois raisons :

| Problème | Cause | Conséquence |
| --- | --- | --- |
| Faux tableau | `page.find_tables()` détecte **toute la page** comme un tableau (bbox `0,0 → 958,539`) | Tous les blocs de texte sont supprimés car « dans le tableau » |
| Texte en double | Le PDF (issu de PowerPoint) contient chaque mot du menu en double, une fois **invisible** | « Év Éalu va atio lun… » dans la grille |
| Pas d'images | Les blocs image (`block[6] == 1`) étaient ignorés | Les logos des clients disparaissent |

La v4 corrige ces trois points et ajoute une sortie **dans l'ordre de lecture**, utilisable pour le RAG.

---

## Vue d'ensemble

```text
            PDF (une page)
                  │
   ┌──────────────┼──────────────────┐
   ▼              ▼                  ▼
extract_lines  extract_images   extract_tables       PARTIE 1 : extraction
   │              │                  │               chaque élément = type + bbox + contenu
   ▼              │                  │
merge_same_row    │                  │
   └──────────────┴────────┬─────────┘
                           ▼
                 liste d'éléments (44 sur la page 24)
                           │
                           ▼
                        xy_cut                        PARTIE 2 : ordre de lecture
                           │
             ┌─────────────┴──────────────┐
             ▼                            ▼
   build_rag_markdown           build_visual_markdown  PARTIES 3 et 4 : les deux sorties
   (<pdf>_rag.md)               (<pdf>_grille.md)
```

Tout le script repose sur une seule idée : **chaque élément de la page est un dictionnaire avec un `type`, une `bbox` (position) et un contenu.**

```python
{"type": "text",  "bbox": Rect(479, 192, 511, 207), "text": "Global", "size": 12.0}
{"type": "image", "bbox": Rect(41, 136, 131, 157),  "path": ".../p16_img1.png"}
{"type": "table", "bbox": Rect(311, 45, 507, 245),  "text": "| Id | Article | Prix |\n..."}
```

Rappel : une **bbox** est un rectangle `(x0, y0, x1, y1)` en points PDF. `x0, y0` est le coin **en haut à gauche**, et `y` augmente vers le bas.

---

## Partie 1 : extraction des éléments

### `extract_lines(page)` : les lignes de texte visibles

**Rôle :** récupérer chaque ligne de texte avec **sa propre bbox** et sa taille de police.

**Différence avec la v3 :** la v3 utilisait `get_text("blocks")`, qui renvoie des blocs entiers. On ne connaît alors que la position du bloc, pas celle de chaque ligne. Ici on utilise `get_text("dict")`, qui descend jusqu'aux **spans** (morceaux de texte avec une même police).

La hiérarchie de `get_text("dict")` :

```text
page → blocks → lines → spans
                         └── {"text", "bbox", "size", "alpha", "font", ...}
```

**Le filtre du texte invisible.** Voici ce que contient vraiment le PDF pour le menu :

```text
'ESSENTIEL'  alpha 0    size 7.5   bbox [31, 18, 63, 27]    ← invisible
'ESSENTIEL'  alpha 255  size 12.0  bbox [39, 21, 97, 36]    ← visible
'Suivi'      alpha 0    size 7.5   bbox [594, 40, 609, 49]  ← invisible
'Suivi'      alpha 255  size 12.0  bbox [602, 44, 624, 59]  ← visible
```

`alpha` est l'opacité (0 = transparent, 255 = opaque). On ne garde que les spans visibles :

```python
spans = [s for s in line["spans"] if s["alpha"] > 0 and s["text"].strip()]
```

On calcule ensuite la bbox **uniquement à partir des spans visibles**. Sinon, la partie invisible « tire » la bbox vers le haut et le mot n'est plus aligné avec ses voisins.

**Résultat sur la page 24 :** 151 lignes. Par exemple, la première ligne du tableau arrive en 7 morceaux séparés :

```python
{'text': 'Global', 'bbox': (479, 192, 511, 207), 'size': 12.0}
{'text': '693',    'bbox': (608, 192, 626, 207), 'size': 12.0}
{'text': '30 %',   'bbox': (649, 192, 673, 207), 'size': 12.0}
{'text': '1 633',  'bbox': (694, 192, 721, 207), 'size': 12.0}
{'text': '70 %',   'bbox': (744, 192, 768, 207), 'size': 12.0}
{'text': '2 326',  'bbox': (791, 192, 818, 207), 'size': 12.0}
{'text': '100 %',  'bbox': (843, 192, 873, 207), 'size': 12.0}
```

C'est le problème que règle la fonction suivante.

---

### `merge_same_row(lines)` : recoller les cellules d'un tableau

**Rôle :** fusionner les textes **courts** qui sont **sur la même ligne visuelle** et **proches**. Cela sert à trois choses :

1. les cellules d'un tableau sans bordures → `"Global | 693 | 30 % | ..."`
2. les mots d'un menu → `"ESSENTIEL | MODÈLE D'AFFAIRES | SOCIAL | ..."`
3. une puce isolée et son texte → `"- Bilan carbone annuel..."`

**Comment ça marche, en deux étapes :**

**Étape 1 : regrouper en lignes visuelles.** On trie les lignes par `y0`. Deux lignes dont les `y0` sont à moins de 3 points font partie de la même ligne visuelle. Chaque ligne visuelle est ensuite triée de gauche à droite (`x0`).

**Étape 2 : fusionner de gauche à droite.** Pour chaque élément, on regarde celui juste à sa gauche (`previous`) :

| Condition | Action |
| --- | --- |
| `previous` est un seul caractère non alphanumérique (`•`, ``…) | c'est une puce : `"- " + texte` |
| les deux font ≤ 25 caractères **et** sont à moins de 150 pt | ce sont des cellules : `previous + " | " + texte` |
| sinon | on les laisse séparés |

**Pourquoi « court » ?** C'est ce qui distingue une cellule de tableau d'une phrase. Sur la page 16, les puces de deux cartes voisines sont aussi sur la même ligne visuelle, mais elles font 40 à 70 caractères : elles ne sont pas fusionnées, et les deux colonnes restent séparées.

**Pourquoi `not isalnum()` pour la puce ?** Sans ça, le chiffre `"1"` (seul dans sa cellule, ligne « RDD ») était pris pour une puce et devenait `"- 11 %"`.

**Résultat sur la page 24 :** on passe de 151 lignes à 44 éléments.

```python
'Global | 693 | 30 % | 1 633 | 70 % | 2 326 | 100 %'   bbox (479, 192, 873, 207)
'Staff | 180 | 43 % | 237 | 57 % | 417 | 18 %'         bbox (479, 209, 873, 224)
'employeur.'                                           bbox (48, 195, 103, 209)   ← pas fusionné : trop loin
```

« employeur. » est sur la même ligne visuelle que « Global », mais à 376 pt de distance : il reste séparé.

---

### `find_repeated_images(doc)` et `extract_images(page, repeated_images)` : les images

**Rôle :** enregistrer chaque image utile en PNG et garder sa position.

On ignore deux types d'images :

- **les toutes petites** (moins de 12 pt de côté) : barres décoratives, puces dessinées ;
- **les images répétées** sur au moins un tiers des pages : logo, bandeau. `find_repeated_images` compte, pour tout le document, sur combien de pages apparaît chaque image (identifiée par son numéro interne `xref`).

Sur la page 24, il y a 2 images, et aucune n'est gardée :

```text
xref 0   bbox [0, 0, 9, 540]       ← barre violette à gauche : 9 pt de large, trop petite
xref 14  bbox [920, 25, 940, 45]   ← logo en haut à droite : présent sur toutes les pages
```

Sur la page 16, les 6 logos clients (Selectra, Bouygues, Framatome…) sont gardés.

**Pourquoi `get_pixmap(clip=bbox)` plutôt qu'extraire l'image brute ?** On fait une « capture d'écran » de la zone. On obtient exactement ce qu'on voit sur la page, même si l'image est recadrée, a un masque de transparence ou est intégrée directement dans la page.

---

### `extract_tables(page)` : les tableaux avec bordures

**Rôle :** utiliser `find_tables()` de PyMuPDF, mais **rejeter les faux positifs**.

Sur la page 24, `find_tables()` trouve ceci :

```text
bbox [0, 0, 958, 539]   1 ligne   2 colonnes   100 % de la page
```

C'est le cadre de la page, pas un tableau. On rejette donc tout tableau qui :

- couvre plus de **50 % de la page**, ou
- a moins de **2 lignes**.

Sur la page 24, il ne reste aucun tableau détecté. Le vrai tableau (sans bordures) est géré par `merge_same_row`. Sur `test_pdf.pdf`, les 2 tableaux avec bordures sont bien gardés.

---

### `extract_elements(page, repeated_images)` : tout rassembler

Elle appelle les trois extractions et **retire les lignes de texte déjà contenues dans un tableau**, pour ne pas les avoir en double :

```python
if not any(line["bbox"] in table["bbox"] for table in tables)
```

(`rect_a in rect_b` est vrai si `rect_a` est entièrement dans `rect_b`.)

**Résultat sur la page 24 :** 44 éléments, dans le désordre. La partie 2 les remet dans l'ordre.

---

## Partie 2 : l'ordre de lecture (XY-cut)

C'est la partie la plus importante pour le RAG. Si on lit une page en 2 colonnes ligne par ligne, on mélange les phrases des deux colonnes. Il faut lire **une zone après l'autre**.

### `largest_gap(elements, axis)` : trouver le plus grand espace vide

On projette toutes les bbox sur un axe (comme leur ombre sur un mur), puis on cherche le plus grand trou.

```text
axis = 1 (axe y) : on cherche une bande horizontale vide → coupe entre deux zones l'une au-dessus de l'autre
axis = 0 (axe x) : on cherche une bande verticale vide   → coupe entre deux colonnes

Exemple sur l'axe x :

  élément A  [====]
  élément B        [=====]
  élément C                        [======]
                          ↑        ↑
                          └─ trou ─┘   ← le plus grand espace vide, on coupe au milieu
```

La fonction renvoie la **taille** du trou et la **position** de la coupe (le milieu du trou).

### `xy_cut(elements)` : couper récursivement

L'algorithme tient en 4 lignes :

1. On cherche le plus grand trou vertical (`gap_x`) et le plus grand trou horizontal (`gap_y`).
2. S'ils sont tous les deux trop petits (`gap_x < 3` et `gap_y < 1.5`), la zone est un **bloc** : on s'arrête.
3. Sinon, on coupe le long du **plus grand** des deux.
4. On recommence dans chacun des deux morceaux (récursivité), d'abord celui du haut ou de gauche.

**Pourquoi le plus grand trou ?** Sur la page 16 (des cartes en 2 rangées de 3), l'espace entre les deux rangées (46 pt) est plus grand que l'espace entre les colonnes (24 pt), qui est lui-même plus grand que l'espace entre le titre et les puces d'une carte (13 pt). Couper au plus grand trou donne donc : rangée 1 → carte 1 → carte 2 → carte 3 → rangée 2 → … C'est l'ordre naturel de lecture.

**Ce qui se passe vraiment sur la page 24 :**

```text
44 éléments  zone [39,21 → 937,521]   gap_x 38.3   gap_y 51.7 à y=476   → coupe horizontale (pied de page à part)
├── 42 éléments  zone [39,21 → 887,450]   gap_x 0      gap_y 16.7 à y=67  → coupe horizontale (menu à part)
│   ├── 2 éléments  zone [39,21 → 855,59]      → les 2 lignes du menu
│   └── 40 éléments zone [39,75 → 887,450]     → on continue à couper :
│         - titre « Égalité femmes-hommes » / reste de la page
│         - colonne de gauche (texte) / colonne de droite (tableau), coupe verticale à x=470
│         - puis chaque paragraphe et chaque ligne du tableau
└── 2 éléments   zone [469,502 → 937,521]  gap_x 84.7 à x=883 → « Index Egapro 2025 : ... » / numéro de page
```

Résultat : 32 groupes, dans l'ordre de lecture.

**Pourquoi `merge_same_row` est indispensable ici :** sans lui, le tableau est fait de cellules séparées par des trous de 20 à 90 pt. Ces trous sont plus grands que l'espace entre le texte de gauche et le tableau (4,8 pt). L'algorithme couperait donc le tableau en colonnes, et on lirait « 693, 180, 137… » au lieu de « Global | 693 | 30 % … ». Une fois les lignes du tableau fusionnées, il n'y a plus de trou à l'intérieur.

---

## Partie 3 : le Markdown pour le RAG

### `render_group(group, body_size)` : un groupe → du texte

Pour chaque groupe renvoyé par `xy_cut` :

- les **images** deviennent `![image](images_v4/.../p16_img1.png)` ;
- les **tableaux** gardent leur texte Markdown ;
- les **lignes de texte** sont recollées en paragraphe, **sauf** les puces (`- …`) et les lignes de tableau (`… | …`), qui gardent chacune leur propre ligne ;
- si la police est au moins **1,4 fois** plus grande que le texte courant, c'est un **titre** : on ajoute `### `.

### `build_rag_markdown(elements, page_number)` : la page entière

1. Elle calcule `body_size`, la taille de police « normale » de la page : la médiane des tailles (12 pt sur la page 24).
2. Elle appelle `xy_cut`, puis `render_group` sur chaque groupe.
3. Elle ajoute avant chaque groupe un **commentaire avec sa position** :

```markdown
<!-- page=24 bbox=48,133,468,209 -->
Nous nous engageons à assurer une égalité salariale stricte entre les femmes et les hommes ...

<!-- page=24 bbox=479,192,873,207 -->
Global | 693 | 30 % | 1 633 | 70 % | 2 326 | 100 %
```

C'est ainsi qu'on « respecte la position » dans le RAG : le texte est dans l'ordre de lecture (bon pour les embeddings), et chaque morceau garde sa page et ses coordonnées. On peut les mettre dans les métadonnées des chunks dans Qdrant, pour retrouver la source exacte d'une réponse.

---

## Partie 4 : la grille visuelle (debug)

### `build_visual_markdown(page, elements, page_number)`

C'est la même idée que ta v3 : une grille de caractères où chaque élément est placé selon sa bbox. Elle sert à **vérifier à l'œil** que l'extraction est juste. Elle n'est pas faite pour le RAG.

Deux améliorations par rapport à la v3 :

**1. Chaque élément est placé à sa propre position.** En v3, la ligne `i` d'un bloc était placée à `ligne du bloc + i`. Dès que la taille de police changeait, les lignes se décalaient. Ici, chaque ligne a sa propre bbox.

**2. La largeur d'un caractère est calculée, pas fixe.** En v3, `char_width = 3.5`. Mais une ligne de 80 caractères en 12 pt fait ≈ 400 pt dans le PDF, contre 80 × 3,5 = 280 pt dans la grille : le texte débordait sur la colonne voisine et des caractères étaient perdus. On calcule maintenant, pour chaque ligne, `largeur / nombre de caractères`, et on prend une valeur basse (10 % des lignes sont plus serrées) :

```python
widths = sorted(e["bbox"].width / len(e["text"]) for e in texts if len(e["text"]) >= 5)
char_width = max(widths[len(widths) // 10], 2.5)
```

Sur la page 24 : `char_width = 4.82`, soit une grille de 200 colonnes.

---

## Le programme principal

```python
with pymupdf.open(PDF_PATH) as doc:
    repeated_images = find_repeated_images(doc)          # une seule fois pour tout le document

    for page_number in PAGES or range(1, len(doc) + 1):  # PAGES = None → toutes les pages
        page = doc[page_number - 1]                      # les pages commencent à 0 dans PyMuPDF
        elements = extract_elements(page, repeated_images)

        if not elements:                                 # page scannée : il faudra de l'OCR
            ...
        rag_markdown.append(build_rag_markdown(elements, page_number))
        visual_markdown.append(build_visual_markdown(page, elements, page_number))
```

**Pour l'utiliser :** modifier `PDF_PATH` et `PAGES` en haut du fichier, puis lancer `python comparaison_extraction4.py`.

**Sorties, dans `data/processed/` :**

- `<pdf>_rag.md` : pour le RAG ;
- `<pdf>_grille.md` : pour vérifier ;
- `images_v4/<pdf>/` : les images en PNG.

---

## Les réglages (seuils)

Ce sont les valeurs à ajuster si un nouveau PDF sort mal :

| Où | Valeur | Rôle |
| --- | --- | --- |
| `merge_same_row` | `< 3` pt | Deux textes sont sur la même ligne visuelle |
| `merge_same_row` | `<= 25` caractères | Un texte est assez court pour être une cellule |
| `merge_same_row` | `< 150` pt | Deux cellules sont assez proches pour être fusionnées |
| `extract_images` | `< 12` pt | Image trop petite → décorative |
| `find_repeated_images` | 1/3 des pages | Image répétée → logo ou bandeau |
| `extract_tables` | `> 50 %` de la page | Faux tableau |
| `xy_cut` | `gap_x < 3` et `gap_y < 1.5` | Plus rien à couper : c'est un bloc |
| `render_group` | `>= 1.4 ×` la taille normale | C'est un titre |

---

## Limites connues

- **Texte dessiné en vectoriel** : sur la page 24, « INDEX ÉGAPRO 2025 » et « Groupe, pondéré par effectif » sont des formes, pas du texte. Il faudrait de l'OCR. Même chose pour les PDF scannés (la page sort avec `<!-- page sans texte : OCR nécessaire -->`).
- **Titres en gras de même taille que le texte** : ils ne sont pas reconnus comme titres et sont collés au paragraphe (c'est le cas dans `test_pdf.pdf`). On pourrait utiliser le gras (`span["flags"]`) en plus de la taille.
- **Ordre image / texte dans un même groupe** : si un groupe contient à la fois une image et du texte, le texte sort avant l'image. En pratique, `xy_cut` isole presque toujours les images.
- **Menu de navigation** : il se répète sur chaque page et ajoute du bruit dans le RAG. Il est gardé pour respecter toutes les positions, mais on pourrait le retirer.
- **Seuils réglés sur ce document** : ils doivent être vérifiés sur des mises en page différentes.
