export type Page = {id:string;role:string;title:string;body:string;highlights:string[];visual_direction:string;narration:string;review_flags:string[]};
export type Project = {id:string;revision:number;aspect_ratio?:'9:16'|'16:9';pace:number;created_at:string;generation_meta:{model:string};content:{title:string;source_summary:string;audience:string;style:string;pages:Page[];closing_cta:string}};
export type Settings = {base_url:string;model:string;key_configured:boolean};
export async function api<T>(path:string, method='GET', data?:unknown):Promise<T>{
 const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});
 if(!r.ok){let message='请求失败';try{const e=await r.json();message=typeof e.detail==='string'?e.detail:'输入格式不正确，请检查字段长度与内容。'}catch{message='后端暂时不可用，请检查服务是否启动。'}throw new Error(message)}return r.json();
}
