-- =============================================================================
-- DATA-LOW — schéma de données (annexe B du manuscrit, version 2.0 corrigée)
--
-- Corpus de productions d'élèves STEM contextualisées + journal Low-Eval Kit.
-- Ajouts par rapport à la version 1.0 de l'ancien Low-Eval-Kit :
--   * colonne ``runs.metadonnees`` (JSON) : les huit métadonnées de
--     reproductibilité de la section 7.2 du manuscrit (version du code,
--     révision des poids, paramètres de décodage, prompt complet,
--     quantification, matériel, nombre d'exécutions, politique de cache) ;
--   * colonne ``runs.vram_gb`` : pic mémoire GPU réellement mesuré
--     (l'ancien code terrain écrivait un 0.0 factice) ;
--   * tables d'annotation double et d'arbitrage pour le contrôle qualité
--     (double annotation n = 150 puis arbitrage, section 2.4).
-- =============================================================================
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. Exercices collectés (section 2.5 : un identifiant unique par exercice)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercises (
    id            TEXT PRIMARY KEY,        -- ex. « MATH-2023-SN-012 »
    source        TEXT NOT NULL,           -- examen / manuel / concours
    year          INTEGER,
    serie         TEXT,
    discipline    TEXT NOT NULL,           -- mathématiques, physique, SNT…
    statement     TEXT NOT NULL,           -- énoncé (OCR contrôlé)
    images        TEXT,                    -- chemins des images associées (JSON)
    solution_ref  TEXT NOT NULL,           -- solution de référence
    concepts      TEXT NOT NULL,           -- concepts STEM attendus (JSON)
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. Annotations d'erreurs (taxonomie du tableau 2.4)
--    Les cinq valeurs contrôlées correspondent exactement aux cinq types
--    validés par l'étude pilote ; toute autre valeur est rejetée.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS annotations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id   TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    annotator     TEXT NOT NULL,
    error_type    TEXT NOT NULL CHECK (error_type IN
                  ('conceptuelle', 'procedurale', 'visuo-spatiale',
                   'linguistique', 'calculatoire')),
    span          TEXT,                    -- segment textuel ou visuel localisé
    concept       TEXT,
    rationale     TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (exercise_id, annotator, error_type, span)
);

-- ---------------------------------------------------------------------------
-- 2 bis. Double annotation et arbitrage (contrôle qualité, section 2.4)
--    Le sous-échantillon de 150 exercices est annoté deux fois ; les
--    désaccords sont versés dans ``arbitrages`` avec la décision finale.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS double_annotations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id    TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    annotateur_a   TEXT NOT NULL,
    annotateur_b   TEXT NOT NULL,
    type_a         TEXT NOT NULL CHECK (type_a IN
                   ('conceptuelle', 'procedurale', 'visuo-spatiale',
                    'linguistique', 'calculatoire')),
    type_b         TEXT NOT NULL CHECK (type_b IN
                   ('conceptuelle', 'procedurale', 'visuo-spatiale',
                    'linguistique', 'calculatoire')),
    accord         INTEGER NOT NULL CHECK (accord IN (0, 1)),
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (exercise_id, annotateur_a, annotateur_b)
);

CREATE TABLE IF NOT EXISTS arbitrages (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id    TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    arbitre        TEXT NOT NULL,
    decision       TEXT NOT NULL CHECK (decision IN
                   ('conceptuelle', 'procedurale', 'visuo-spatiale',
                    'linguistique', 'calculatoire')),
    justification  TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 3. Journal des exécutions (reproductibilité : versions, graines, mesures)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model         TEXT NOT NULL,
    environment   TEXT NOT NULL CHECK (environment IN ('cloud', 'local', 'terrain')),
    quantization  TEXT NOT NULL DEFAULT 'nf4',
    seed          INTEGER NOT NULL,
    started_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    metadonnees   TEXT,                    -- JSON : huit métadonnées §7.2
    memory_gb     REAL,                    -- pic mémoire RAM mesuré (psutil)
    vram_gb       REAL,                    -- pic mémoire GPU mesuré (pynvml/CUDA)
    latency_ms    REAL,
    energy_kwh    REAL                     -- estimation CodeCarbon
);

-- ---------------------------------------------------------------------------
-- 4. Résultats par exercice (métriques CA et UP du chapitre 2)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    exercise_id    TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    prediction     TEXT,
    f1             REAL,                   -- détection d'erreur
    precision_at_k REAL,                   -- localisation
    bertscore_f1   REAL,                   -- diagnostic causal (contrôle humain requis)
    concept_recall REAL,                   -- couverture des concepts
    actionable     INTEGER,                -- actionnabilité (0/1, jugement humain)
    clarity        REAL,                   -- clarté (échelle humaine)
    readability    REAL,                   -- lisibilité (écart à la cible)
    adaptability   REAL                    -- adaptabilité au profil
);

-- Index de lecture : agrégations par (modèle, environnement) et par run.
CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_exercise ON results(exercise_id);
CREATE INDEX IF NOT EXISTS idx_runs_model_env ON runs(model, environment);
CREATE INDEX IF NOT EXISTS idx_annotations_exercise ON annotations(exercise_id);
