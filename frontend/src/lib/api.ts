export type ModelId = 'granite-ttm-r3'|'seasonal-naive';
export type Frequency = 'D'|'h';
export interface Point { timestamp:string; value:number; }
export interface ForecastPoint extends Point { q10:number|null; q90:number|null; }
export interface ForecastResponse { model:string; model_revision:string|null; frequency:Frequency; horizon:number; observations_used:number; history:Point[]; forecast:ForecastPoint[]; warnings:string[]; latency_ms:number; quantiles_available:boolean; }
export interface ModelStatus { default:string; models:{id:string;loaded:boolean;revision:string|null;context_length:number;prediction_length:number;error:string|null}[]; }
export interface BacktestResponse { model:string; mean_mae:number;mean_rmse:number;mean_smape:number;windows:{start:string;end:string;mae:number;rmse:number;smape:number;mase:number|null}[];warnings:string[]; }

async function checked(res:Response) {
  if(!res.ok){ const body=await res.json().catch(()=>null); const detail=body?.detail; throw new Error(typeof detail==='string'?detail:(detail?.message || JSON.stringify(detail) || `HTTP ${res.status}`)); }
  return res.json();
}
export const api = {
  models: async (): Promise<ModelStatus> => checked(await fetch('/api/v1/models')),
  forecastFile: async (file:File, opts:{model:ModelId;frequency:Frequency;horizon:number;timestampColumn:string;valueColumn:string;seasonalPeriod:number}):Promise<ForecastResponse>=>{
    const fd=new FormData();fd.set('file',file);fd.set('model_name',opts.model);fd.set('frequency',opts.frequency);
    fd.set('horizon',String(opts.horizon));fd.set('timestamp_column',opts.timestampColumn);fd.set('value_column',opts.valueColumn);fd.set('seasonal_period',String(opts.seasonalPeriod));
    return checked(await fetch('/api/v1/forecast/file',{method:'POST',body:fd}));
  },
  backtest: async (points:Point[], opts:{model:ModelId;frequency:Frequency;horizon:number;seasonalPeriod:number}):Promise<BacktestResponse>=> checked(await fetch('/api/v1/forecast/backtest',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({points,model:opts.model,frequency:opts.frequency,horizon:opts.horizon,seasonal_period:opts.seasonalPeriod,windows:2})
  }))
};
export function parseCSV(text:string, timestampColumn='timestamp', valueColumn='value'):Point[]{
  // Sample/backtesting parser only; server handles authoritative CSV validation and parsing.
  const rows=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/); const headers=rows.shift()?.split(',').map(s=>s.trim()) || [];
  const t=headers.indexOf(timestampColumn),v=headers.indexOf(valueColumn); if(t<0||v<0) throw Error('ستون تاریخ یا مقدار پیدا نشد');
  return rows.map(row=>{const cells=row.split(',');return {timestamp:cells[t]?.trim()||'',value:Number(cells[v])};}).filter(p=>p.timestamp&&Number.isFinite(p.value));
}
export function fmt(value:number,digits=1){return new Intl.NumberFormat('fa-IR',{maximumFractionDigits:digits}).format(value);}
export function errorMessage(err:unknown){return err instanceof Error?err.message:'خطای ناشناخته در درخواست';}
