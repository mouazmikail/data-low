-- =============================================================================
-- DATA-LOW — schéma de données (annexe C du manuscrit, chapitre 2 §5)
-- Corpus de productions d'élèves STEM contextualisées + journal Low-Eval Kit.
--
-- Alignement avec le manuscrit :
--   * table exercises : champs de l'annexe C (exercise_id, year, subject,
--     series, statement_fr, asset_path, answer_fr, source_page) + champs
--     du schéma JSON 2.0 (stem_concepts, bloom_level, source) ;
--   * table erreurs   : référentiel des cinq familles (taxonomie 2.4),
--     joint par id_erreur comme dans les requêtes versionnées (annexe B) ;
--   * table annotations : campagne / annotator / etiquette / arbitre,
--     conformes à la double annotation n = 150 (chapitre 2 §4.4) ;
--   * tables runs + results : journal des huit métadonnées (§ 7.2) et
--     métriques brutes + normalisées (tableau 3.1).
-- =============================================================================
PRAGMA foreign_keys = ON;

-- Référentiel des familles d'erreurs (taxonomie du tableau 2.4). Peuplé
-- idémpôtement par annotation_store.init_db() ; l'ordre des id est stable.
CREATE TABLE IF NOT EXISTS erreurs (
    id_erreur   INTEGER PRIMARY KEY,
    type_erreur TEXT NOT NULL UNIQUE
                  CHECK (type_erreur IN
                  ('conceptuelle', 'procedurale', 'visuo-spatiale',
                   'linguistique', 'calculatoire'))
);

-- Exercices collectés (section 2.5 : un identifiant unique par exercice).
-- Champs annexe C : exercise_id, year, subject, series, statement_fr,
-- asset_path, answer_fr, source_page. Les champs JSON (asset_path,
-- stem_concepts) stockent des tableaux sérialisés.
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id    TEXT PRIMARY KEY,        -- ex. « TCD-MATH-1995-C-01 »
    year           INTEGER,                 -- année de la session
    subject        TEXT NOT NULL,           -- mathematiques, physique, SNT…
    series         TEXT CHECK (series IN ('C', 'D', 'E')),
    statement_fr   TEXT NOT NULL,           -- énoncé (OCR contrôlé)
    asset_path     TEXT,                    -- chemins des images associées (JSON)
    answer_fr      TEXT NOT NULL,           -- corrigé de référence
    source_page    INTEGER,                 -- page du sujet source
    stem_concepts  TEXT,                    -- concepts STEM attendus (JSON)
    bloom_level    TEXT,                    -- taxonomie de Bloom (tableau 2.6)
    source         TEXT,                    -- archive_officielle / manuel…
    schema_version TEXT NOT NULL,           -- version du format JSON d'origine
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Annotations d'erreurs (double annotation n = 150, § 4.4). L'étiquette
-- finale après arbitrage porte arbitre = 1 (requêtes de l'annexe B).
CREATE TABLE IF NOT EXISTS annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id TEXT NOT NULL REFERENCES exercises(exercise_id)
                ON DELETE CASCADE,
    campagne    TEXT NOT NULL DEFAULT 'double_annotation_2026',
    annotator   TEXT NOT NULL,              -- ex. « expert_1 », « expert_2 »
    id_erreur   INTEGER NOT NULL REFERENCES erreurs(id_erreur),
    location    TEXT,                       -- segment textuel ou visuel localisé
    diagnostic  TEXT,                       -- justification de l'annotateur
    stem_concept TEXT,                      -- concept STEM en cause
    arbitre     INTEGER NOT NULL DEFAULT 0, -- 1 = étiquette finale (arbitrage)
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (exercise_id, campagne, annotator, id_erreur, location)
);

-- Journal des exécutions (huit métadonnées du § 7.2 + tableau 3.1).
CREATE TABLE IF NOT EXISTS runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    model             TEXT NOT NULL,
    environment       TEXT NOT NULL
                      CHECK (environment IN ('cloud', 'local', 'terrain')),
    quantization      TEXT NOT NULL DEFAULT 'nf4',
    seed              INTEGER NOT NULL,
    -- métadonnées § 7.2
    code_version      TEXT,                 -- tag ou hash court Git
    weights_version   TEXT,                 -- révision HF des poids (hash)
    decoding_json     TEXT,                 -- paramètres de décodage (JSON)
    prompt_hash       TEXT,                 -- SHA-256 du prompt complet
    template_id       TEXT,                 -- gabarit PromptEngine
    template_version  TEXT,                 -- version du gabarit
    hardware_json     TEXT,                 -- snapshot matériel (JSON)
    n_warmup          INTEGER NOT NULL DEFAULT 0,
    cache_policy      TEXT NOT NULL DEFAULT 'hf_hub_default',
    model_config_json TEXT,                 -- fiche modèle (models.yaml)
    -- mesures
    memory_gb         REAL,                 -- pic mesuré (psutil)
    latency_ms        REAL,                 -- moyenne par exercice
    energy_kwh        REAL,                 -- CodeCarbon (rapportée à part)
    extra_json        TEXT,                 -- champs libres (incidents, stats)
    started_at        TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at       TEXT
);

-- Résultats par exercice : métriques CA brutes ET normalisées (tableau 3.1,
-- exigence « valeurs brutes et normalisées »), plus les indicateurs UP
-- humains lorsqu'ils sont disponibles.
CREATE TABLE IF NOT EXISTS results (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    exercise_id        TEXT NOT NULL REFERENCES exercises(exercise_id)
                       ON DELETE CASCADE,
    prediction         TEXT,
    latency_ms         REAL,                -- latence de CET exercice
    f1                 REAL,                -- détection d'erreur (brute)
    precision_at_k     REAL,                -- localisation (brute)
    bertscore_f1       REAL,                -- diagnostic (analyse secondaire)
    concept_recall     REAL,                -- couverture des concepts (brute)
    norm_f1            REAL,                -- valeurs normalisées [0, 1]
    norm_precision_at_k REAL,
    norm_bertscore_f1  REAL,
    norm_concept_recall REAL,
    actionable         INTEGER,             -- actionnabilité (0/1, humain)
    clarity            REAL,                -- clarté (échelle humaine)
    readability        REAL,                -- lisibilité L = 1 − D/Dmax
    adaptability       REAL                 -- adaptabilité au profil
);

CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_model_env ON runs(model, environment);
CREATE INDEX IF NOT EXISTS idx_annotations_campagne ON annotations(campagne);
