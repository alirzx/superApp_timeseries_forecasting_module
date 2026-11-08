import React, {useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import ForecastChart from './components/ForecastChart';
import {api,parseCSV,fmt,errorMessage} from './lib/api';
import type {ForecastResponse,BacktestResponse,ModelStatus,ModelId,Frequency,Point} from './lib/api';
import './style.css';

function App(){
  const [model,setModel]=useState<ModelId>('granite-ttm-r3');
  const [frequency,setFrequency]=useState<Frequency>('D');
  const [horizon,setHorizon]=useState(12);
  const [season,setSeason]=useState(7);
  const [dateCol,setDateCol]=useState('timestamp');
  const [valueCol,setValueCol]=useState('value');
  const [file,setFile]=useState<File|null>(null);
  const [points,setPoints]=useState<Point[]>([]);
  const [result,setResult]=useState<ForecastResponse|null>(null);
  const [backtest,setBacktest]=useState<BacktestResponse|null>(null);
  const [status,setStatus]=useState<ModelStatus|null>(null);
  const [loading,setLoading]=useState(false);
  const [assessing,setAssessing]=useState(false);
  const [error,setError]=useState('');
  const [active,setActive]=useState<'overview'|'forecast'|'history'>('overview');
  const [drag,setDrag]=useState(false);
  const chooser=useRef<HTMLInputElement>(null);
  const manualFileChosen=useRef(false);
  const [apiConnectionFailed,setApiConnectionFailed]=useState(false);
  useEffect(()=>{
    let active=true;
    const refresh=()=>{api.models().then(s=>{if(active){setStatus(s);setApiConnectionFailed(false);}})
      .catch(()=>{if(active){setStatus(null);setApiConnectionFailed(true);}});};
    refresh();
    const timer=window.setInterval(refresh,10000);
    return ()=>{active=false;window.clearInterval(timer);};
  },[]);
  // Preload the bundled CSV; selecting a user file always takes priority.
  useEffect(()=>{
    let active=true;
    fetch('/sample-energy.csv').then(async r=>{
      if(!r.ok)throw Error('Sample CSV unavailable');
      const content=await r.text();
      const sample=parseCSV(content);
      if(active&&!manualFileChosen.current){
        setFile(new File([content],'sample-energy.csv',{type:'text/csv'}));
        setPoints(sample);
        setFrequency('h');setHorizon(24);setSeason(24);
      }
    }).catch(e=>{if(active&&!manualFileChosen.current)setError(errorMessage(e));});
    return ()=>{active=false;};
  },[]);
  const modelStatus=status?.models.find(s=>s.id===model);
  async function choose(f:File){manualFileChosen.current=true;setFile(f);setResult(null);setBacktest(null);setError('');try {const text=await f.text();setPoints(f.name.endsWith('.csv')?parseCSV(text,dateCol,valueCol):[]);}catch{setPoints([]);}}
  async function loadSample(){manualFileChosen.current=false;try {const r=await fetch('/sample-energy.csv');if(!r.ok)throw Error('فایل نمونه در دسترس نیست'); const body=await r.blob(); await choose(new File([body],'sample-energy.csv',{type:'text/csv'}));setFrequency('h');setHorizon(24);setSeason(24);}catch(e){setError(errorMessage(e));}}
  async function submit(){if(!file)return;setLoading(true);setError('');setBacktest(null);try{const r=await api.forecastFile(file,{model,frequency,horizon,timestampColumn:dateCol,valueColumn:valueCol,seasonalPeriod:season});setResult(r);setActive('forecast');}catch(e){setError(errorMessage(e));}finally{setLoading(false);}}
  async function evaluate(){if(!points.length){setError('برای اعتبارسنجی، یک فایل CSV با ستون‌های timestamp و value بارگذاری کنید.');return;}setAssessing(true);setError('');try{setBacktest(await api.backtest(points,{model,frequency,horizon,seasonalPeriod:season}));setActive('history');}catch(e){setError(errorMessage(e));}finally{setAssessing(false);}}
  function exportJSON(){if(!result)return;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.download='superapp-forecast.json';a.click();URL.revokeObjectURL(a.href);}
  const last=result?.history.at(-1)?.value??null;
  const predicted=result?.forecast.at(-1)?.value??null;
  const delta=(predicted!==null&&last!==null&&Math.abs(last)>1e-9)?(predicted-last)/Math.abs(last)*100:null;
  const visibleHistory=result?.history||points.slice(-110);
  return <div className="shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark">◈</span><div><strong>SuperApp <b>AI</b></strong><small>داشبورد هوش مصنوعی</small></div></div>
      <div className="nav-caption">فضای کاری</div>
      <nav><button onClick={()=>setActive('overview')} className={active==='overview'?'selected':''}><span>▦</span>نمای کلی</button><button onClick={()=>setActive('forecast')} className={active==='forecast'?'selected':''}><span>⌁</span>پیش‌بینی سری زمانی</button><button onClick={()=>setActive('history')} className={active==='history'?'selected':''}><span>▤</span>ارزیابی مدل</button></nav>
      <div className="sidebar-bottom"><div className="side-gradient"><span className="side-mini">ماژول پنجم</span><strong>Time Series<br/>Forecasting</strong><span>Granite TTM-R3 · CPU</span></div><div className="app-version">SUPERAPP / MODULE 05 <span>v0.1.0</span></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb">سوپر اپ <span> / </span> هوش مصنوعی <span> / </span> <b>پیش‌بینی سری زمانی</b></div><div className="top-actions"><span className={'status-chip '+(modelStatus?.loaded?'good':'warm')}><i/>{modelStatus?.loaded?'مدل آماده است':apiConnectionFailed?'ارتباط با API برقرار نیست':status?'مدل در حال آماده‌سازی است':'در حال بررسی وضعیت مدل'}</span><span className="avatar">AI</span></div></header>
      <div className="content">
        <div className="heading"><div><div className="eyebrow">TIME-SERIES INTELLIGENCE <span>●</span> MODULE 05</div><h1>پیش‌بینی سری زمانی</h1><p>داده‌های تاریخی را به دیدگاهی روشن از آینده تبدیل کنید؛ سریع، سبک و کاملاً روی CPU.</p></div><div className="head-right"><span>⚡</span><div><b>Granite TinyTimeMixer R3</b><small>Zero-shot · On-premise</small></div></div></div>
        <div className="stats-grid"><div className="stat-card"><div className="stat-top">نقاط داده <span>▥</span></div><div className="stat-value">{fmt(result?.observations_used||points.length,0)} <small>رکورد</small></div><div className="stat-foot">داده تاریخی ورودی</div></div><div className="stat-card"><div className="stat-top">افق پیش‌بینی <span>↗</span></div><div className="stat-value">{fmt(horizon,0)} <small>گام آینده</small></div><div className="stat-foot">قابل تنظیم براساس نیاز</div></div><div className="stat-card"><div className="stat-top">زمان استنتاج <span>◷</span></div><div className="stat-value">{result?fmt(result.latency_ms,0):'—'} <small>میلی‌ثانیه</small></div><div className="stat-foot">مدت محاسبه درخواست اخیر</div></div><div className="stat-card accent"><div className="stat-top">تغییر پیش‌بینی <span>⌁</span></div><div className="stat-value">{delta===null?'—':`${delta>=0?'+':''}${fmt(delta,1)}%`}</div><div className="stat-foot">نسبت به آخرین مقدار تاریخی</div></div></div>
        <div className="grid-main"><section className="card setup-card"><div className="card-head"><div><span className="step-label">01 / تنظیمات</span><h2>آماده‌سازی پیش‌بینی</h2><p>داده را وارد کرده و تنظیمات را انتخاب کنید.</p></div><span className="card-symbol">⚙</span></div>
            <div className="field-label">بارگذاری داده <small>CSV / JSON</small></div><div className={'dropzone '+(drag?'is-drag':'')} onDragOver={e=>{e.preventDefault();setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);if(e.dataTransfer.files[0])void choose(e.dataTransfer.files[0]);}} onClick={()=>chooser.current?.click()} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter')chooser.current?.click();}}><div className="upload-icon">⇧</div><strong>{file?file.name:'فایل سری زمانی را اینجا رها کنید'}</strong><span>{file?'برای تغییر فایل کلیک کنید':'یا برای انتخاب فایل از دستگاه کلیک کنید'}</span><input ref={chooser} hidden type="file" accept=".csv,.json" onChange={e=>{if(e.target.files?.[0])void choose(e.target.files[0]);}}/></div>
            <button className="sample-link" onClick={loadSample}>✦ بازنشانی داده نمونه: مصرف انرژی (۷۲۰ ساعت)</button>{file?.name==='sample-energy.csv'&&<div className="form-hint">✓ فایل نمونه ۷۲۰ ساعته به‌صورت خودکار آماده شده است. برای مشاهده پیش‌بینی دکمه اجرا را انتخاب کنید.</div>}
            <div className="separator"/>
            <label className="field-label" htmlFor="model">موتور پیش‌بینی</label><select id="model" value={model} onChange={e=>setModel(e.target.value as ModelId)}><option value="granite-ttm-r3">Granite TTM-R3 (مدل اصلی)</option><option value="seasonal-naive">Seasonal Naive (مرجع آماری)</option></select>
            <div className="two-cols"><div><label className="field-label" htmlFor="freq">فاصله زمانی</label><select id="freq" value={frequency} onChange={e=>setFrequency(e.target.value as Frequency)}><option value="D">روزانه</option><option value="h">ساعتی</option></select></div><div><label className="field-label" htmlFor="horizon">افق آینده</label><select id="horizon" value={horizon} onChange={e=>setHorizon(Number(e.target.value))}>{[6,12,24,30].map(n=><option value={n} key={n}>{fmt(n,0)} گام</option>)}</select></div></div>
            <div className="two-cols"><div><label className="field-label" htmlFor="tcol">ستون تاریخ</label><input id="tcol" value={dateCol} onChange={e=>setDateCol(e.target.value)} dir="ltr"/></div><div><label className="field-label" htmlFor="vcol">ستون مقدار</label><input id="vcol" value={valueCol} onChange={e=>setValueCol(e.target.value)} dir="ltr"/></div></div>
            <label className="field-label" htmlFor="season">دوره فصلی مدل آماری</label><input id="season" type="number" min={1} max={168} value={season} onChange={e=>setSeason(Number(e.target.value))} /><div className="form-hint">این گزینه فقط برای Seasonal Naive کاربرد دارد.</div>
            <button className="primary-action" disabled={!file||loading} onClick={submit}>{loading?'در حال محاسبه…':'اجرای پیش‌بینی'} <span>←</span></button>
            {error&&<div className="alert-error" role="alert">⚠ {error}</div>}
            <div className="privacy-note">♢ پردازش محلی روی CPU، بدون ارسال داده به سرویس ابری</div></section>
          <div className="results-col"><section className="card graph-card"><div className="card-head chart-head"><div><span className="step-label">02 / نتایج</span><h2>تحلیل روند و پیش‌بینی</h2><p>نمایش تاریخچه و چشم‌انداز مقادیر آینده</p></div><div className="chart-actions"><span className="model-pill">{result?.model || 'منتظر داده'}</span><button onClick={exportJSON} disabled={!result} className="export-btn">↓ خروجی JSON</button></div></div><ForecastChart history={visibleHistory} forecast={result?.forecast||[]}/>{result?.warnings.length?<div className="warning-box">{result.warnings.join(' · ')}</div>:null}<div className="chart-bottom"><span>● تاریخچه</span><span>● ناحیه پیش‌بینی</span><small>{result?.quantiles_available?'بازه‌های چندکی مدل نمایش داده شده‌اند':'بازه عدم‌قطعیت تنها در صورت تأیید مدل نمایش داده می‌شود'}</small></div></section>
          <section className="card table-card"><div className="card-head"><div><span className="step-label">03 / داده‌ها</span><h2>خروجی نقاط آینده</h2><p>خلاصه مقادیر پیش‌بینی‌شده</p></div><span className="subtle-tag">{result?`${fmt(result.forecast.length,0)} نقطه`:'بدون خروجی'}</span></div><div className="table-scroll"><table><thead><tr><th>ردیف</th><th>تاریخ / زمان</th><th>مقدار پیش‌بینی</th><th>Q10</th><th>Q90</th></tr></thead><tbody>{result?.forecast.slice(0,10).map((p,i)=><tr key={p.timestamp}><td>{fmt(i+1,0)}</td><td dir="ltr">{new Date(p.timestamp).toLocaleString('fa-IR',{dateStyle:'short',timeStyle:frequency==='h'?'short':undefined})}</td><td className="result-amount">{fmt(p.value,2)}</td><td>{p.q10===null?'—':fmt(p.q10,2)}</td><td>{p.q90===null?'—':fmt(p.q90,2)}</td></tr>)||<tr><td colSpan={5} className="empty-table">پس از اجرای مدل، خروجی پیش‌بینی در این بخش نشان داده می‌شود.</td></tr>}</tbody></table></div></section></div></div>
        <section className="bottom-panel"><div><span className="step-label">04 / اعتبارسنجی</span><h2>بررسی کیفیت پیش‌بینی</h2><p>ارزیابی تاریخی روی دو پنجره زمانی بدون آموزش مدل و بدون نشت اطلاعات آینده.</p></div><div className="eval-actions">{backtest&&<div className="eval-kpis"><span>MAE <b>{fmt(backtest.mean_mae,2)}</b></span><span>RMSE <b>{fmt(backtest.mean_rmse,2)}</b></span><span>sMAPE <b>{fmt(backtest.mean_smape,1)}%</b></span></div>}<button disabled={assessing||!file} onClick={evaluate}>{assessing?'در حال ارزیابی…':'اجرای Backtest ↖'}</button></div></section>
        <footer>SUPERAPP AI · MODULE 05 <span>Granite TTM-R3 • CPU-Only Forecasting Service</span></footer>
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
