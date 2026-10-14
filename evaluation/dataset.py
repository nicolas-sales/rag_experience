import pandas as pd

def build_dataset():
    data = [
        {
            "question": "Quelle est l'activité de Davidson Consulting?",
            "reference": "Davidson consulting se positionne comme un acteur du conseil en management et expertises technologiques",
            "references_page": [5]
        },
        {
            "question": "Quelle est la date de l'ntranet communautaire DUTLER?",
            "reference": "2005 Intranet communautaire DUTLER.",
            "references_page": [6]
        },
        {
            "question": "Quelle est l'impact societal?",
            "reference": " Mesurer. Solidav, 1‰ de chiffres d'affaires; Réduire. Achats responsables, éthique des missions, Augmenter. Solidav, mécénat, redirection ODD, ancrage local. Partager. Embarquer, exemplarité, partenariats.",
            "references_page": [7]
        },
        {
            "question": "Quelles sont nos certifications auditées?",
            "reference": "B Corp : Certifiée depuis 2018, recertifiée en 2026, valable jusqu'au 10 juillet 2029. Distinction Best for the World Workers en 2022. ISO 9001:2015: Management de la qualité, certifiée depuis 2015, ISO/IEC 27001:2022 : Management de la sécurité de l'information. Qualiopi : Organisme de formation certifié, Davidson Institute.",
            "references_page": [9]
        },
        {
            "question": "De qui est composé l'équipe impact rattachée à la Direction générale?",
            "reference": "Maêliss Delacroix, Océane Serpin, Thomas Tailhandier",
            "references_page": [10]
        },
        {
            "question": "Quelle est le CA annuel de 2023?",
            "reference": "19215",
            "references_page": [14]
        },
        {
            "question": "Quelle est le total de nouvelles missions ODD en 2022?",
            "reference": "52",
            "references_page": [14]
        },
        {
            "question": "Quelle est la mission de redirection ecologique de Eudonet?",
            "reference": "Formation à l’écoconception numérique des parties prenantes du projet. Audit de l’existant. Rédaction d’un guide d’écoconception adapté au contexte d’Eudonet. Réalisation de l’Analyse de Cycle de Vie d’un service numérique. Définition et priorisation d’actions de transition",
            "references_page": [16]
        },
        {
            "question": "Quelle est la mission de redirection ecologique de Decathlon?",
            "reference": "Participation à la démarche d’écoconception du catalogue de Décathlon. Au sein des équipes de Design : définition des leviers de réduction d’impacts des produits  « vélos », selon le gain environnemental, le coût et la faisabilité. Au sein des équipes de Gestion de la qualité de données : mise en place d’une gouvernance et définition de process pour maîtriser les données utiles au calcul de l’impact des produits",
            "references_page": [16]
        },
        {
            "question": "Comment limiter l'empreinte de nos prestations sur la mobilité Domicile-Travail?",
            "reference": "Proposer du télétravail dès que possible, sans altérer la qualité de nos prestations ou la confiance de nos clients. Encourager les collaborateurs à privilégier les mobilités durables grâce à des dispositifs particuliers (Forfait Mobilité Durable) ou une aide spécifique. Ex : prêt temporaire d’un vélo",
            "references_page": [17]
        },
        {
            "question": "A combien de km sont situés nos clients de nos agences en 2025?",
            "reference": "Moins de 80 km",
            "references_page": [18]
        },
        {
            "question": "Quel est le nombre global de femme en nombre et en pourcentage en 2025?",
            "reference": "693, 30%",
            "references_page": [24]
        },
        {
            "question": "Quelle est la politique de l'inclusion des personnes en situation de handicap?",
            "reference": "Nous garantissons que chaque collaborateur et collaboratrice soit pleinement intégré(e), quels que soient son état de santé et son handicap. Notre politique se fonde sur l'accessibilité, l'adaptation des postes et la sensibilisation continue des équipes, pour recruter, maintenir dans l'emploi et faire évoluer les personnes en situation de handicap.",
            "references_page": [25]
        },
        {
            "question": "Quel est le trust index, comparaison 2024, echelle 0-100 pour Davidson?",
            "reference": "83%",
            "references_page": [29]
        },
        {
            "question": "Quels sont les résultats de SoliDav en 2025?",
            "reference": "283 enagé(e)s, 1782 heures, 563 missions, 74 associations",
            "references_page": [36]
        },
        {
            "question": "Quels sont nos engagements environnementaux?",
            "reference": "Notre trajectoire de réduction, validée par SBTi, constitue la structure de nos engagements environnementaux : elle oriente et ordonne nos actions. Nos politiques environnementales s'appliquent à l'ensemble du Groupe. Par exemple, notre bilan carbone tient compte de l’ensemble de nos filiales, présentes dans six pays : France, Belgique, Espagne, Luxembourg, Suisse et Canada. Nous mesurons, réduisons puis, seulement ensuite, contribuons à hauteur de nos émissions incompressibles et historiques, sans jamais revendiquer la neutralité carbone. Le numérique responsable et les achats responsables restent nos deux leviers d'application transverses, au même titre que pour nos impacts sociaux et sociétaux.",
            "references_page": [42]
        },
        {
            "question": "Quel est le bilan carbone en tCO2e en 2025?",
            "reference": "7590 tCO2e",
            "references_page": [44]
        },
        {
            "question": "Quel est l'objectif S1 et S2 en 2032?",
            "reference": "<422 tCO2e",
            "references_page": [45]
        },
        {
            "question": "Quel est la politique des données e sécurité de l'information?",
            "reference": "Chaque collaborateur(rice) accède à des informations qui sont la propriété de notre société mais aussi régulièrement de tiers, clients et sous-traitants. Nous devons tous protéger la confidentialité des données dont nous disposons et nous assurer qu'elles ne soient transmises que dans un cadre professionnel légitime. Nous entendons prévenir tout délit d'initié et toute divulgation d'informations privilégiées, car ces pratiques érodent la confiance que nous voulons construire avec chacun de nos partenaires.",
            "references_page": [54]
        },
        {
            "question": "De combien est le financement associatif à Amnesty Internationnal France en 2025?",
            "reference": "10 000 €",
            "references_page": [55]
        },
        {
            "question": "Qels sont principaux engagements Right Tech?",
            "reference": "01 MESURER ET PILOTER : Analyse de cycle de vie de notre DSI et de nos services de conseil. Audit de maturité Right Tech de la DSI, réalisé chaque année. 02 RÉDUIRE LES EXTERNALITÉS NÉGATIVES : Application des bonnes pratiques de notre guide d'écoconception dans nos projets DSI.Politique de sobriété : achats IT responsables, réparabilité, allongement de la durée de vie des matériels, gestion de la seconde vie.Intervention chez nos clients pour mesurer l'impact de leur DSI et construire leur plan de sobriété.plan de sobriété. 03 AUGMENTER LES EXTERNALITÉS POSITIVES : Co-fondation du consortium DECeNZ pour produire de nouveaux communs sur la sobriété numérique.Contribution aux référentiels de bonnes pratiques d'écoconception GreenIT.fr.Conception de plateformes de partage de contenus à impact, ouvertes au grand public.",
            "references_page": [58]
        }
    ]

    return pd.DataFrame(data)


if __name__ == "__main__":

    from pathlib import Path

    df = build_dataset()

    output_path = Path(__file__).resolve().parent / "dataset.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(df.to_string(index=False))
    print(f"\nDataset sauvegardé : {output_path}")