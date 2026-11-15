# Frontend smoke script

Run `npm run dev`, open http://127.0.0.1:3000, and use synthetic inputs only.

1. Open the eye-procedure sample. Save preferences and continue through Documents to Care plan.
2. Verify **one** frequency conflict, both exact source quotes, unknown duration/refills, and disabled completion boxes for conflicted instructions.
3. Open Understand, generate brief and detailed explanations, switch EN/ES, and confirm the original quotes stay unchanged. Tap a term and give feedback; inspect the profile counters.
4. Answer teach-back with either frequency. Expect `source_conflict`, with no schedule confirmed.
5. Select the side-effects concern. Expect `side_effect` and `wants_to_stop`. Confirm or correct labels, save, and verify the concern log.
6. Generate a message. Verify only selected concerns and conflicts appear, edit it, and copy it. There must be no send action.
7. Load the blood-pressure sample. Expect exactly `dose_mismatch` and `action_mismatch`.
8. In Documents change 20 mg to 10 mg and replace `Avoid NSAIDs, including ibuprofen.` with `Continue ibuprofen as needed.` Confirm synthetic data and rebuild. Expect zero conflicts.
9. Load the matching pair. Answer `20 mg twice daily` and `20 mg dos veces al día`; expect dose and frequency errors. `10 mg once daily` and `10 mg una vez al día` match the quote. An incomplete/uncertain answer must not be marked understood.
10. Try voice in seeded mode; verify a typed fallback explanation appears. Connected testing must also cover denied microphone permission and backend transcription errors.
11. Enter `No puedo respirar.` in the concern flow. Expect the urgent screen, blocked normal navigation, and an accessible demo-reset control. Do not actually call the demo's emergency link.
12. Reset. Verify cases, concerns, history, drafts, and learned scores are cleared.
13. Use a phone-width viewport (393 × 852 was checked in Chrome). Check navigation, source cards, text entry, message controls, profile/evaluation access, and reset.
14. Evaluation → Load saved results: seeded mode must say no evaluation is available, with no fabricated metrics.
15. After connecting FastAPI, repeat against the deployed frontend and verify CORS, explicit response mode, saved evaluation artifact counts, speech transcription, and OCR failure fallback.

## Observed in this build

Desktop Chrome: cornea selection → setup → source-linked conflict → explanation → term tap → conflict-first teach-back → barrier labels → confirmed concern → generated draft containing concern and both quotes → successful copy notification.

Chrome iPhone 16 emulation (393 × 852): responsive message layout, Spanish navigation, Spanish urgent interruption, reachable reset dialog, and successful reset to the Spanish landing page.

The local Chrome profile's Grammarly extension injected body attributes and produced a development hydration warning. The displayed Next.js diff identified only `data-new-gr-c-s-check-loaded` and `data-gr-ext-installed`. No application hydration mismatch was identified. Use an extension-free browser profile when rehearsing the demo.

Not yet verified: hosted URL, actual physical phone, live backend, live microphone transcription/denial, OCR, and backend ML metrics.
