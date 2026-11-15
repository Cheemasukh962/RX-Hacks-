import type { EvalResult } from '@/lib/types';

type Metric = { n: number; exact_match: number; micro?: { precision: number; recall: number; f1: number }; macro_f1?: number; per_label?: Record<string, { precision: number; recall: number; f1: number; support: number }> };
type Split = { description?: string; counts?: { teachback?: number; barrier?: number; by_language?: Record<string, number> }; teachback?: Record<string, Metric | null>; barrier?: Record<string, Metric | null> };
type SavedResults = { generated_at?: string; framing?: string; heldout_status?: string; splits?: Record<string, Split | null> };
const percent = (value: number | undefined) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—';

export function EvaluationDashboard({ data, spanish }: { data: EvalResult; spanish: boolean }) {
  const results = data.eval_results as SavedResults | null | undefined;
  const t = (en: string, es: string) => spanish ? es : en;
  if (!results?.splits) return <p>{t('No saved classifier results are available yet.', 'Aún no hay resultados guardados del clasificador.')}</p>;
  return <div className="evaluation-dashboard">
    <p>{results.framing}</p>
    {results.generated_at && <p className="helper">{t('Saved run', 'Ejecución guardada')}: {results.generated_at}</p>}
    {Object.entries(results.splits).map(([name, split]) => <section key={name} className="evaluation-split">
      <h3>{name === 'synthetic_test' ? t('Synthetic test set', 'Prueba sintética') : name === 'reviews_silver' ? t('Silver-labeled reviews', 'Reseñas con etiquetas provisionales') : name === 'heldout' ? t('Human-written held-out set', 'Prueba independiente escrita por personas') : name.replaceAll('_', ' ')}</h3>
      {!split ? <p className="notice notice-warning">{name === 'heldout' ? results.heldout_status ?? t('Human examples have not been collected.', 'Faltan los ejemplos humanos.') : t('No results saved for this split.', 'Sin resultados guardados.')}</p> : <>
        <p className="helper">{split.description}</p>
        <p className="helper">{t('Examples', 'Ejemplos')}: {split.counts?.teachback ?? 0} teach-back · {split.counts?.barrier ?? 0} {t('barrier', 'barreras')} · {Object.entries(split.counts?.by_language ?? {}).map(([language, count]) => `${language}: ${count}`).join(' · ')}</p>
        {(['teachback', 'barrier'] as const).map(task => {
          const models = Object.entries(split[task] ?? {}).filter((entry): entry is [string, Metric] => !!entry[1] && typeof entry[1].n === 'number' && entry[1].n > 0);
          if (!models.length) return null;
          return <div key={task}><h4>{task === 'teachback' ? t('Teach-back', 'Comprensión') : t('Barrier classification', 'Clasificación de barreras')}</h4><div className="table-scroll" tabIndex={0} role="region" aria-label={`${name} ${task}`}><table><caption className="sr-only">{name} · {task}</caption><thead><tr><th>{t('System', 'Sistema')}</th><th>{t('Exact matches', 'Coincidencias exactas')}</th><th>Micro F1</th><th>Macro F1</th><th>{t('Precision', 'Precisión')}</th><th>Recall</th></tr></thead><tbody>{models.map(([model, metric]) => <tr key={model}><th scope="row">{model.replaceAll('_', ' ')}</th><td>{metric.exact_match} / {metric.n} <small>({percent(metric.exact_match / metric.n)})</small></td><td>{percent(metric.micro?.f1)}</td><td>{percent(metric.macro_f1)}</td><td>{percent(metric.micro?.precision)}</td><td>{percent(metric.micro?.recall)}</td></tr>)}</tbody></table></div><details className="label-results"><summary>{t('Inspect per-label results', 'Ver resultados por etiqueta')}</summary>{models.map(([model, metric]) => <div key={model}><h4>{model.replaceAll('_', ' ')}</h4><div className="table-scroll" tabIndex={0} role="region" aria-label={`${task} ${model} labels`}><table><thead><tr><th>{t('Label', 'Etiqueta')}</th><th>F1</th><th>{t('Precision', 'Precisión')}</th><th>Recall</th><th>{t('Support', 'Ejemplos positivos')}</th></tr></thead><tbody>{Object.entries(metric.per_label ?? {}).map(([label, value]) => <tr key={label}><th scope="row">{label.replaceAll('_', ' ')}</th><td>{percent(value.f1)}</td><td>{percent(value.precision)}</td><td>{percent(value.recall)}</td><td>{value.support}</td></tr>)}</tbody></table></div></div>)}</details></div>;
        })}
      </>}
    </section>)}
    <section className="evaluation-split"><h3>{t('Style-learning simulation', 'Simulación de preferencias')}</h3><p>{t('Simulation · not patient outcomes.', 'Simulación · no son resultados de pacientes.')}</p>{data.bandit_sim ? <><p className="helper">{t('A simulation artifact is available. Its chart schema has not been agreed yet; the original data is preserved below.', 'Hay datos de simulación. Falta acordar el formato de la gráfica; se conservan los datos originales.')}</p><details><summary>{t('Inspect simulation artifact', 'Ver datos de simulación')}</summary><pre>{JSON.stringify(data.bandit_sim, null, 2)}</pre></details></> : <p className="helper">{t('Waiting for the backend simulation artifact. No simulated values have been invented.', 'Esperando los datos de simulación del backend. No se inventaron valores.')}</p>}</section>
    <details><summary>{t('Inspect original saved response', 'Ver respuesta original guardada')}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>
  </div>;
}
