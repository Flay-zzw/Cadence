import {forwardRef} from 'react';
import {Page} from './types';
import icons from './slide-icons.json';
import visualRules from './visual-rules.json';

export const roles:Record<string,string>={cover:'开篇',hook:'看见问题',concept:'核心概念',explain:'原理拆解',example:'场景应用',myth:'认知纠偏',summary:'重点回顾',cta:'行动指南'};
const roleIcons:Record<string,keyof typeof icons>={cover:'spark',hook:'bulb',concept:'bulb',explain:'layers',example:'target',myth:'target',summary:'check',cta:'arrow'};
export function SlideIcon({name}:{name:keyof typeof icons}){return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name].map((d,i)=><path key={i} d={d}/>)}</svg>}
export function paragraphs(text:string){return text.split(/\n+/).filter(s=>s.trim()).flatMap(block=>{const sentences=block.match(/[^。！？!?]+[。！？!?]*|[。！？!?]+/g)||[block];const result:string[]=[];let buffer='';for(const sentence of sentences){buffer+=sentence;if(buffer.length>=45){result.push(buffer);buffer=''}}if(buffer)result.push(buffer);return result})}
export function pointParts(text:string){const clean=text.replace(/^[\s,，]*(?:[•·\-]|[（(]?\d+[）).、．])\s*/, '');const split=clean.search(/[：:]/);return split>0&&split<=12?{title:clean.slice(0,split),detail:clean.slice(split+1).trim()}:{title:clean,detail:''}}
export function hasPlaceholder(text:string){return text.split(/[：:\n]/).some(part=>new Set(['短标题','小标题','要点标题','具体说明','具体内容','示例标题','填写标题','填写内容','待补充','待填写','标题','说明','短标题具体说明','小标题具体说明']).has(part.replace(/[\s{}<>《》【】\[\]（）()*_`#>，,。.!！?？、/\\-]/g,'')))}
export function semanticIcon(text:string,fallback:keyof typeof icons='bulb'):keyof typeof icons{return (visualRules.topics.find(topic=>topic.keywords.some(keyword=>text.toLowerCase().includes(keyword)))?.icon as keyof typeof icons)||fallback}
const Slide=forwardRef<HTMLElement,{page:Page;index:number;count:number;video:boolean}>(function Slide({page,index,count,video},ref){
 const cover=page.role==='cover';
 const topic=semanticIcon(page.title,semanticIcon(page.body,roleIcons[page.role]||'bulb'));
 const points=page.highlights.filter(h=>!hasPlaceholder(h));
 return <article ref={ref} className={'slide '+(video?'landscape':'portrait')+' role-'+page.role}>
  <div className="eyebrow"><span className="deck-brand"><i/> 知识切片</span><span>{String(index+1).padStart(2,'0')} / {String(count).padStart(2,'0')}</span></div>
  <div className="slide-heading"><div className="slide-category"><span className="topic-symbol"><SlideIcon name={topic}/></span><span>{roles[page.role]||'知识讲解'}</span><span className="category-line"/></div><h1>{page.title}</h1></div>
  <div className="body">{paragraphs(page.body).map((p,i)=><p key={i}>{p}</p>)}</div>
  {cover&&<div className="cover-art" aria-hidden="true"><span className="art-orbit"/><span className="art-sticker sticker-left"><SlideIcon name="bulb"/></span><span className="art-sticker sticker-main"><SlideIcon name={topic}/></span><span className="art-sticker sticker-right"><SlideIcon name="spark"/></span><span className="art-dot dot-one"/><span className="art-dot dot-two"/></div>}
  <div className="concepts">{points.map((h,i)=>{const point=pointParts(h);return <div className="concept" key={i}><span className="concept-icon"><SlideIcon name={semanticIcon(h,(['target','layers','arrow'] as const)[i%3])}/></span><div className="concept-copy"><strong>{point.title}</strong>{point.detail&&<p>{point.detail}</p>}</div></div>})}</div>
  <footer><span>保持好奇，把知识变成行动。</span><span className="footer-mark">CADENCE <span>✦</span></span></footer>
 </article>
});
export default Slide;
