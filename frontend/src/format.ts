import type { Analysis, Candidate, Job } from "./types";

export const timeLabel = (seconds: number) => {
  const value = Math.floor(seconds);
  return `${String(Math.floor(value / 3600)).padStart(2, "0")}:${String(Math.floor(value / 60) % 60).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
};
export const dateLabel = (value: string) =>
  new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
export const statusLabel: Record<Job["status"], string> = {
  queued: "Na fila",
  running: "Processando",
  completed: "Concluído",
  failed: "Falhou",
  cancelled: "Cancelado",
};

function repeatedPhrase(text: string) {
  const words = text.toLocaleLowerCase("pt-BR").match(/[\p{L}\p{N}]+/gu) || [];
  if (words.length < 12) return false;
  for (let width = 1; width <= Math.min(8, Math.floor(words.length / 4)); width++) {
    for (let start = 0; start <= words.length - width * 4; start++) {
      const phrase = words.slice(start, start + width).join(" ");
      let count = 1;
      while (words.slice(start + count * width, start + (count + 1) * width).join(" ") === phrase) count++;
      if (count >= 4 && count * width >= words.length * 0.6) return true;
    }
  }
  for (let width = 3; width <= Math.min(6, Math.floor(words.length / 4)); width++) {
    const counts = new Map<string, number>();
    for (let index = 0; index <= words.length - width; index++) {
      const phrase = words.slice(index, index + width).join(" ");
      counts.set(phrase, (counts.get(phrase) || 0) + 1);
    }
    if ([...counts.values()].some((count) => count >= 4 && count * width >= words.length * 0.25)) return true;
  }
  return false;
}
export function description(candidate: Candidate, analysis: Analysis) {
  const transcript = analysis.evidence.transcript
    .filter((item) => candidate.evidence_ids.includes(item.evidence_id));
  if (transcript.some((item) => repeatedPhrase(item.observation)))
    return "Transcrição repetitiva neste trecho. Revise o vídeo ou gere uma nova análise.";
  const speech = transcript
    .map((item) => item.observation)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  const words = speech.toLowerCase().match(/\w+/g) || [];
  const counts = new Map<string, number>();
  for (const word of words) counts.set(word, (counts.get(word) || 0) + 1);
  if (words.length >= 12 && Math.max(...counts.values()) / words.length > 0.45)
    return "A transcrição não permite um resumo confiável deste trecho.";
  if (speech)
    return speech.length > 140 ? `${speech.slice(0, 140).trim()}…` : speech;
  if (candidate.features.visual_changes)
    return "Mudança visual observada. Revise o vídeo para identificar o acontecimento.";
  return "Revise este corte para identificar o assunto.";
}
