import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

// One of the app's own risk cards, used so new pictures match their flat style.
const STYLE_REFERENCE = "https://media.base44.com/images/public/6afa4cb44fe8de88eb21169e/f13dddc7e_generated_image.png";

// Draws one illustration for a chat answer. The picture only shows what the answer already says.
export const generateVisual = createServerFn({ method: "POST" })
  .validator(z.object({ text: z.string().min(1).max(600) }))
  .handler(async ({ data, context }) => {
    const prompt = `A single flat-style illustration that helps a patient understand this health message:

"${data.text}"

Match the style of the reference image: flat shapes, warm stone and cream background, one signal-red accent, calm everyday scene with one or two people.
Show only what the message says. Do not add any other medical idea.
No words, letters, numbers, labels or logos anywhere in the picture.
Nothing graphic: no blood, wounds, needles or frightening imagery. Square format.`;
    // Base44-only fallback: off Base44 hosting (e.g. Vercel) there are no platform headers, so report a failed draw.
    try {
      const { url } = await context.getBase44().asServiceRole.integrations.Core.GenerateImage({
        prompt,
        existing_image_urls: [STYLE_REFERENCE],
      });
      return { url };
    } catch {
      return { failed: true };
    }
  });