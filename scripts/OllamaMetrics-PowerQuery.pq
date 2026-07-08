// =============================================================================
// OllamaMetrics — Power Query M  (paste into Excel > Data > Get Data > From Other > Blank Query)
//
// SETUP:
//   1. Open Excel > Data tab > Get Data > Launch Power Query Editor
//   2. Home > New Source > Blank Query
//   3. Home > Advanced Editor — paste this entire file
//   4. Change CsvPath to your actual path (keep the double-backslashes)
//   5. Click Done, then Close & Load To... > Table
// =============================================================================

let
    // -------------------------------------------------------------------------
    // CONFIG — update CsvPath to match your OutputDir from the PS script
    // -------------------------------------------------------------------------
    CsvPath = "C:\Users\" & Text.From(Diagnostics.ActivityId()) & "\OllamaMetrics\ollama_metrics.csv",
    // Simpler alternative: hard-code your path, e.g.:
    // CsvPath = "C:\Users\rdavi\OllamaMetrics\ollama_metrics.csv",

    // -------------------------------------------------------------------------
    // 1. Load raw CSV
    // -------------------------------------------------------------------------
    RawCsv = Csv.Document(
        File.Contents(CsvPath),
        [
            Delimiter   = ",",
            Columns     = 30,
            Encoding    = 65001,      // UTF-8
            QuoteStyle  = QuoteStyle.Csv
        ]
    ),

    // -------------------------------------------------------------------------
    // 2. Promote headers
    // -------------------------------------------------------------------------
    WithHeaders = Table.PromoteHeaders(RawCsv, [PromoteAllScalars = true]),

    // -------------------------------------------------------------------------
    // 3. Cast every column to the correct type
    // -------------------------------------------------------------------------
    Typed = Table.TransformColumnTypes(WithHeaders, {
        // Identity / audit
        {"RunId",                 type text},
        {"Timestamp",             type datetime},
        {"ModelName",             type text},
        {"ModelFamily",           type text},
        {"ParameterSize",         type text},
        {"QuantLevel",            type text},
        {"PromptLabel",           type text},
        {"PromptHash",            type text},
        {"WarmupRuns",            Int64.Type},
        {"RepeatRuns",            Int64.Type},

        // Latency (milliseconds)
        {"AvgWallClockMs",        type number},
        {"AvgTotalDurationMs",    type number},
        {"AvgLoadDurationMs",     type number},
        {"AvgPromptEvalMs",       type number},
        {"AvgGenDurationMs",      type number},

        // Token counts
        {"AvgPromptTokenCount",   Int64.Type},
        {"AvgGenTokenCount",      Int64.Type},

        // Throughput
        {"AvgTokensPerSec",       type number},
        {"AvgPromptTokensPerSec", type number},
        {"AvgResponseLength",     Int64.Type},

        // Memory
        {"OllamaProcessRamMB",    type number},
        {"OllamaModelVramMB",     type number},
        {"SystemRamUsedMB",       type number},

        // GPU
        {"GpuName",               type text},
        {"VramUsedMB",            type number},
        {"VramFreeMB",            type number},
        {"VramTotalMB",           type number},
        {"GpuUtilizationPct",     type number},
        {"GpuTempC",              type number},

        {"Notes",                 type text}
    }),

    // -------------------------------------------------------------------------
    // 4. Add calculated columns
    // -------------------------------------------------------------------------

    // Total latency excluding model load (pure inference cost)
    WithInferenceMs = Table.AddColumn(
        Typed, "InferenceOnlyMs",
        each [AvgTotalDurationMs] - [AvgLoadDurationMs],
        type number
    ),

    // VRAM efficiency: tokens generated per MB of VRAM consumed
    WithVramEfficiency = Table.AddColumn(
        WithInferenceMs, "TokensPerVramMB",
        each if [OllamaModelVramMB] > 0
             then Number.Round([AvgGenTokenCount] / [OllamaModelVramMB], 3)
             else null,
        type number
    ),

    // Cost index: lower is better (ms per output token)
    WithCostIndex = Table.AddColumn(
        WithVramEfficiency, "MsPerOutputToken",
        each if [AvgGenTokenCount] > 0
             then Number.Round([AvgGenDurationMs] / [AvgGenTokenCount], 3)
             else null,
        type number
    ),

    // VRAM utilisation % of total GPU VRAM
    WithVramPct = Table.AddColumn(
        WithCostIndex, "VramUtilisationPct",
        each if [VramTotalMB] > 0
             then Number.Round([VramUsedMB] / [VramTotalMB] * 100, 1)
             else null,
        type number
    ),

    // Date only (for time-series slicers in pivot tables)
    WithDate = Table.AddColumn(
        WithVramPct, "RunDate",
        each DateTime.Date([Timestamp]),
        type date
    ),

    // Short model label for chart axes (strip ":latest")
    WithShortName = Table.AddColumn(
        WithDate, "ModelShortName",
        each Text.Replace([ModelName], ":latest", ""),
        type text
    ),

    // -------------------------------------------------------------------------
    // 5. Sort newest first
    // -------------------------------------------------------------------------
    Sorted = Table.Sort(WithShortName, {{"Timestamp", Order.Descending}})

in
    Sorted
