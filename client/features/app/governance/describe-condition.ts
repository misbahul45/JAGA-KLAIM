type Predicate = { fact: string; op: string; value: unknown };

const OPERATORS: Record<string, string> = {
  eq: "=",
  ne: "≠",
  gt: ">",
  gte: "≥",
  lt: "<",
  lte: "≤",
  in: "∈",
};

function render(predicate: Predicate): string {
  return `${predicate.fact} ${OPERATORS[predicate.op] ?? predicate.op} ${JSON.stringify(predicate.value)}`;
}

export function describeCondition(condition: Record<string, unknown>): string[] {
  const all = (condition.all as Predicate[] | undefined) ?? [];
  const any = (condition.any as Predicate[] | undefined) ?? [];
  if (all.length === 0 && any.length === 0) return ["Aturan penampung (tanpa kondisi)"];
  return [
    ...all.map((predicate) => `dan ${render(predicate)}`),
    ...any.map((predicate) => `atau ${render(predicate)}`),
  ];
}
