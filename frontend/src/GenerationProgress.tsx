import {useEffect,useState} from 'react';
import {Check,Loader2} from 'lucide-react';
import {GenerationJob} from './types';
import './progress.css';

const stages=[['queued','等待开始'],['planning','素材分析与大纲'],['writing','逐页生成'],['validating','内容校验'],['saving','保存项目']];
function elapsed(start:string|null|undefined,end:string|null|undefined,now:number){
 if(!start)return '—';
 const seconds=Math.max(0,Math.floor(((end?Date.parse(end):now)-Date.parse(start))/1000));
 return seconds<60?`${seconds} 秒`:`${Math.floor(seconds/60)} 分 ${seconds%60} 秒`;
}
export default function GenerationProgress({job,connectionError}:{job:GenerationJob;connectionError:string}){
 const [now,setNow]=useState(Date.now());
 const active=job.status==='queued'||job.status==='running';
 useEffect(()=>{setNow(Date.now());if(!active)return;const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[job.id,active]);
 const current=job.pages?.find(p=>p.index===job.current_page);
 const currentStage=job.stages?.find(s=>s.id===job.stage);
 return <section className="generation-progress" aria-label="生成进度">
  <div className="progress-heading"><div><span className="progress-kicker">创作进度</span><h2 role="status">{active?<Loader2 className="spin" size={19}/>:job.status==='completed'?<Check size={19}/>:null}{job.message}</h2></div><span className={'job-badge '+job.status}>{job.status==='completed'?'已完成':job.status==='failed'?'已停止':connectionError?'正在重连':'进行中'}</span></div>
  {connectionError&&<p role="alert" className="progress-warning">{connectionError} 正在自动重连，以下为最后收到的进度。</p>}
  <div className="progress-metrics">
   <div><span>总耗时</span><strong>{elapsed(job.created_at,job.finished_at,now)}</strong></div>
   <div><span>页面进度</span><strong>{job.total_pages?`${job.completed_pages??0} / ${job.total_pages} 页已完成`:'正在规划页数'}</strong></div>
   <div><span>{active?'当前页面':'最后处理页面'}</span><strong>{current?`第 ${current.index} 页`:'—'}</strong></div>
   <div><span>{current?'本页耗时':'本阶段耗时'}</span><strong>{current?elapsed(current.started_at,current.finished_at||job.finished_at,now):elapsed(currentStage?.started_at,currentStage?.finished_at||job.finished_at,now)}</strong></div>
  </div>
  <ol className="progress-stages">{stages.map(([id,label])=>{const timing=job.stages?.find(s=>s.id===id);const failed=job.status==='failed'&&job.stage===id;const running=active&&job.stage===id;return <li key={id} className={failed?'failed':running?'active':timing?.finished_at?'done':''}><span>{label}</span><small>{failed?'中断 · ':running?'进行中 · ':timing?.finished_at?'完成 · ':''}{timing?elapsed(timing.started_at,timing.finished_at||job.finished_at,now):'待开始'}</small></li>})}</ol>
  {job.total_pages&&<><progress aria-label="已完成页面" value={job.completed_pages??0} max={job.total_pages}/><ol className="progress-pages">{job.pages?.map(p=><li key={p.index} className={p.status}><b>{String(p.index).padStart(2,'0')}</b><div><span>{p.title}</span><small>{p.status==='pending'?'等待生成':p.status==='running'?(p.attempt>1?'校验修复中':'正在生成'):p.status==='completed'?'已完成':'生成中断'}{p.attempt>1&&` · 第 ${p.attempt} 次内容尝试`}</small></div><time>{elapsed(p.started_at,p.finished_at||job.finished_at,now)}</time></li>)}</ol></>}
  {active&&<p className="progress-note">{job.stage==='planning'&&Number(job.attempt)>1?'大纲校验未通过，正在进行第二次内容尝试。 ':''}耗时实时计时；页面完成后更新进度。模型响应期间可能需要等待，刷新页面可继续查看。</p>}
 </section>;
}
