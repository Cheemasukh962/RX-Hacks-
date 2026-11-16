import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const numbers = (text) => text.match(/\d+(?:[.,]\d+)?/g) || [];

// Rewrites the patient's email draft using their note. Wording only: quotes are added by the app,
// and a rewrite that introduces a number not already in the draft, topic or note is rejected.
export const rewriteEmail = createServerFn({ method: "POST" })
  .validator(z.object({
    body: z.string().min(1).max(3000),
    note: z.string().min(1).max(1500),
    topic: z.string().max(400),
    lang: z.enum(["en", "es"]),
  }))
  .handler(async ({ data, context }) => {
    const prompt = `You help a patient write a short email to their own doctor after a visit.
Rewrite the draft so it clearly includes what the patient says in their note.

Write in ${data.lang === "es" ? "Spanish" : "English"}, first person, polite, plain words (about a 6th-grade reading level), under 150 words.

Rules:
- Use only facts found in the draft, the topic and the patient's note.
- Do not add any number, dose, schedule, diagnosis or medical advice that is not already there.
- Do not say which document is correct. The doctor decides.
- Do not quote the documents. The exact quotes are added below the message separately.
- Start with a greeting. Do not include a subject line, a thank-you line or a signature.

Topic: ${data.topic || "(general question about the visit)"}

Current draft:
${data.body}

Patient's note:
${data.note}`;

    const result = await context.getBase44().asServiceRole.integrations.Core.InvokeLLM({
      prompt,
      response_json_schema: { type: "object", properties: { body: { type: "string" } }, required: ["body"] },
    });
    const allowed = numbers(`${data.body} ${data.note} ${data.topic}`);
    const passed = numbers(result.body).every((n) => allowed.includes(n));
    return { body: passed ? result.body : null };
  });