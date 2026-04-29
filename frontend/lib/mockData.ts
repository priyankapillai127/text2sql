export type Model = "groq" | "ollama";

export interface QueryResult {
  columns: string[];
  rows: (string | number)[][];
  rowCount: number;
  execTimeMs: number;
}

export interface QueryRecord {
  id: string;
  natural: string;
  sql: string;
  status: "ok" | "error" | "repaired";
  ragExamples: number;
  result: QueryResult | null;
  timestamp: string;
  model: Model;
}

export const SCHEMAS: Record<string, string[]> = {
  concert_singer: ["stadium", "singer", "concert", "singer_in_concert"],
  car_1: ["continents", "countries", "car_makers", "model_list", "car_names", "cars_data"],
  student_transcripts: ["addresses", "students", "courses", "transcripts", "transcript_contents"],
  flight_2: ["airlines", "airports", "flights"],
};

export const HISTORY: QueryRecord[] = [
  {
    id: "1",
    natural: "How many singers performed in each stadium?",
    sql: `SELECT s.Name, COUNT(sc.Singer_ID) AS singer_count\nFROM stadium s\nJOIN concert c ON s.Stadium_ID = c.Stadium_ID\nJOIN singer_in_concert sc ON c.Concert_ID = sc.Concert_ID\nGROUP BY s.Stadium_ID, s.Name\nORDER BY singer_count DESC;`,
    status: "ok",
    ragExamples: 3,
    result: {
      columns: ["Name", "singer_count"],
      rows: [
        ["Roden Stadium", 14],
        ["Stark Arena", 11],
        ["Antwerp Expo", 9],
        ["Palace of Sports", 7],
        ["Brisbane Entertainment Centre", 3],
      ],
      rowCount: 5,
      execTimeMs: 12,
    },
    timestamp: "2 min ago",
    model: "groq",
  },
  {
    id: "2",
    natural: "List all stadiums with capacity greater than 10000",
    sql: `SELECT Name, Capacity, Location\nFROM stadium\nWHERE Capacity > 10000\nORDER BY Capacity DESC;`,
    status: "ok",
    ragExamples: 2,
    result: {
      columns: ["Name", "Capacity", "Location"],
      rows: [
        ["Roden Stadium", 45000, "California"],
        ["Stark Arena", 22000, "New York"],
        ["Antwerp Expo", 13500, "Belgium"],
      ],
      rowCount: 3,
      execTimeMs: 8,
    },
    timestamp: "8 min ago",
    model: "groq",
  },
  {
    id: "3",
    natural: "Which singers have performed in more than 3 concerts?",
    sql: `SELECT s.Name, COUNT(sc.Concert_ID) AS concert_count\nFROM singer s\nJOIN singer_in_concert sc ON s.Singer_ID = sc.Singer_ID\nGROUP BY s.Singer_ID, s.Name\nHAVING COUNT(sc.Concert_ID) > 3\nORDER BY concert_count DESC;`,
    status: "repaired",
    ragExamples: 4,
    result: {
      columns: ["Name", "concert_count"],
      rows: [
        ["Tribal King", 7],
        ["Timbaland", 5],
        ["Justin Brown", 4],
      ],
      rowCount: 3,
      execTimeMs: 15,
    },
    timestamp: "15 min ago",
    model: "groq",
  },
];

export const EVAL_METRICS = {
  groq:   { execAcc: 0.82, exactMatch: 0.67, ragBoost: 0.11, queriesRun: 142 },
  ollama: { execAcc: 0.78, exactMatch: 0.61, ragBoost: 0.09, queriesRun: 58  },
};

export const MODEL_LABELS: Record<Model, { name: string; sub: string; tag: string; tagColor: string }> = {
  groq:   { name: "Llama 3.3 70B",  sub: "via Groq · fast", tag: "Groq",  tagColor: "bg-orange-100 text-orange-700" },
  ollama: { name: "Qwen2.5-Coder",  sub: "7B · local",      tag: "local", tagColor: "bg-sky-100 text-sky-700"       },
};
