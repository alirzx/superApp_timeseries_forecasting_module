import { useState } from 'react';
import type { Point, ForecastPoint } from '../lib/api';
import {fmt} from '../lib/api';

export default function ForecastChart({history,forecast}:{history:Point[];forecast:ForecastPoint[]}){
  const [hover,setHover]=useState<number|null>(null);
  const hist=history.slice(-110);const full=[...hist,...forecast];
  const width=940,height=310,pad={t:18,b:40,l:54,r:22};
  if(!full.length) return <div className="empty-chart"><span className="chart-icon">⌁</span><strong>نمودار آماده نمایش است</strong><small>پس از اجرای پیش‌بینی، روند داده و مقادیر آینده اینجا نمایش داده می‌شود.</small></div>;
  const all=[...full.map(x=>x.value),...forecast.map(x=>x.q10??x.value),...forecast.map(x=>x.q90??x.value)];
  let min=Math.min(...all),max=Math.max(...all);const extra=Math.max((max-min)*.14,Math.abs(max)*.02,1);min-=extra;max+=extra;
  const x=(i:number)=>pad.l+i/Math.max(full.length-1,1)*(width-pad.l-pad.r);
  const y=(v:number)=>pad.t+(max-v)/(max-min)*(height-pad.t-pad.b);
  const path=(items:{value:number}[],offset=0)=>items.map((p,i)=>`${i===0?'M':'L'}${x(i+offset).toFixed(2)},${y(p.value).toFixed(2)}`).join(' ');
  const projection=[hist[hist.length-1],...forecast].filter(Boolean) as Point[];
  const start=Math.max(0,hist.length-1);
  const hasRange=forecast.length>0&&forecast.every(p=>p.q10!==null&&p.q90!==null);
  const area=hasRange? [...forecast.map((p,i)=>`${x(hist.length+i)},${y(p.q90!)}`),...forecast.slice().reverse().map((p,i)=>`${x(hist.length+forecast.length-1-i)},${y(p.q10!)}`)].join(' '):'';
  const hoverPoint=hover===null?null:full[hover];
  return <div className="chart-wrap">
    <div className="chart-topline"><span><i className="dot indigo"/>داده تاریخی</span><span><i className="dot teal"/>پیش‌بینی</span>{hasRange&&<span><i className="dot muted"/>بازه ۱۰ تا ۹۰ درصد</span>}</div>
    <svg className="forecast-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="نمودار سری زمانی و مقادیر پیش‌بینی شده">
      <defs><linearGradient id="futureArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#1db3a6" stopOpacity=".23"/><stop offset="1" stopColor="#1db3a6" stopOpacity=".03"/></linearGradient></defs>
      {[0,1,2,3,4].map(i=>{const val=min+(max-min)*i/4,py=y(val);return <g key={i}><line x1={pad.l} x2={width-pad.r} y1={py} y2={py} stroke="#e9edf5" strokeDasharray="4 6"/><text x={pad.l-10} y={py+4} fontSize="12" fill="#8794a9" textAnchor="end">{fmt(val,0)}</text></g>;})}
      <rect x={x(hist.length-1)} y={pad.t} width={width-pad.r-x(hist.length-1)} height={height-pad.t-pad.b} fill="#e8f9f6" opacity=".38" />
      {hasRange&&<polygon points={area} fill="url(#futureArea)"/>}
      <line x1={x(hist.length-1)} x2={x(hist.length-1)} y1={pad.t} y2={height-pad.b} stroke="#87d9cb" strokeDasharray="5 5"/>
      <path d={path(hist)} fill="none" stroke="#6479d7" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      <path d={path(projection,start)} fill="none" stroke="#0eae9d" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      {[0,1,2,3,4].map(i=>{const idx=Math.floor((full.length-1)*i/4),date=new Date(full[idx].timestamp);return <text key={i} x={x(idx)} y={height-11} textAnchor="middle" fill="#8794a9" fontSize="12">{Number.isNaN(date.valueOf())?'':date.toLocaleDateString('fa-IR',{month:'short',day:'numeric'})}</text>})}
      {full.map((_,i)=><rect key={i} x={x(i)-Math.max(2,(width-pad.l-pad.r)/full.length/2)} y={pad.t} width={Math.max(4,(width-pad.l-pad.r)/full.length)} height={height-pad.t-pad.b} fill="transparent" onMouseEnter={()=>setHover(i)} onMouseLeave={()=>setHover(null)}/>)}
      {hover!==null&&<g pointerEvents="none"><line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={height-pad.b} stroke="#929bb1" strokeDasharray="3 5"/><circle cx={x(hover)} cy={y(full[hover].value)} r="5" fill={hover<hist.length?'#6479d7':'#0eae9d'} stroke="white" strokeWidth="2"/></g>}
    </svg>
    {hoverPoint&&<div className="chart-tooltip"><strong>{fmt(hoverPoint.value,2)}</strong><span>{new Date(hoverPoint.timestamp).toLocaleString('fa-IR')}</span></div>}
  </div>;
}
