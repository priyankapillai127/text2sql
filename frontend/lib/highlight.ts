const KEYWORDS = ["SELECT","FROM","WHERE","JOIN","LEFT","RIGHT","INNER","OUTER","ON","GROUP BY","ORDER BY","HAVING","LIMIT","INSERT","UPDATE","DELETE","CREATE","DROP","ALTER","AS","AND","OR","NOT","IN","IS","NULL","LIKE","BETWEEN","EXISTS","UNION","ALL","DISTINCT","CASE","WHEN","THEN","ELSE","END","WITH","ASC","DESC","BY","INTO","VALUES","SET","TABLE","INDEX","VIEW","COUNT","SUM","AVG","MAX","MIN","COALESCE","NULLIF","CAST","ILIKE","SIMILAR"];
const FUNCTIONS = ["COUNT","SUM","AVG","MAX","MIN","COALESCE","NULLIF","CAST","LENGTH","TRIM","UPPER","LOWER","SUBSTR","REPLACE","ROUND","FLOOR","CEIL","NOW","DATE","STRFTIME","GROUP_CONCAT","STRING_AGG","ROW_NUMBER","RANK","DENSE_RANK","LAG","LEAD"];

export function highlightSQL(sql: string): string {
  let result = sql
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // strings
  result = result.replace(/'([^']*)'/g, `<span class="text-amber-600">'$1'</span>`);

  // functions (before keywords so they don't get double-wrapped)
  FUNCTIONS.forEach((fn) => {
    result = result.replace(
      new RegExp(`\\b(${fn})\\s*(?=\\()`, "gi"),
      `<span class="text-emerald-700 font-medium">$1</span>`
    );
  });

  // keywords
  KEYWORDS.forEach((kw) => {
    result = result.replace(
      new RegExp(`\\b(${kw})\\b`, "gi"),
      `<span class="text-sky-700 font-semibold">$1</span>`
    );
  });

  return result;
}
