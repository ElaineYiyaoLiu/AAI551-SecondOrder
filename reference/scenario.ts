import { defaults, type Params } from './model';

export const controls = [
  {key:'substitution',min:0,max:60,step:1},
  {key:'productivity',min:0,max:100,step:1},
  {key:'speed',min:0,max:25,step:1},
  {key:'ubi',min:0,max:2000,step:50},
  {key:'tax',min:0,max:40,step:1}
] as const;
export const presets = [
  {id:'slow', en:'Slow adoption', zh:'AI 缓慢普及', description:['More time for firms and workers to adapt.','AI 普及较慢，企业和劳动者有更多时间适应。'], params:{...defaults,speed:5}},
  {id:'augmentation', en:'Rapid augmentation', zh:'AI 辅助为主', description:['Higher productivity, less labor substitution.','AI 快速普及，主要提升生产率，较少替代劳动。'], params:{...defaults,speed:20,substitution:10,productivity:60}},
  {id:'substitution', en:'Rapid substitution', zh:'AI 替代为主', description:['Faster adoption with more labor displaced.','AI 快速普及，更多劳动被自动化替代。'], params:{...defaults,speed:20,substitution:45,productivity:40}}
];

// Deliberately local and rule based. Never infer unprovided industry calibration.
export function parseQuestion(question:string) {
  const p={...defaults}; const matched:(keyof Params)[]=[];
  const patterns: [keyof Params,RegExp][] = [
    ['substitution', /(?:automat\w*|substitut\w*|replace\w*|自动化|替代)[^\d%％]{0,30}(\d+(?:\.\d+)?)\s*[%％]/i],
    ['productivity', /(?:productivity|生产率|生产力)[^\d%％]{0,20}(\d+(?:\.\d+)?)\s*[%％]/i],
    ['speed', /(?:adoption|普及速度|普及率|采用速度|采用率)[^\d%％]{0,20}(\d+(?:\.\d+)?)\s*[%％]/i],
    ['tax', /(?:tax|税)[^\d%％]{0,25}(\d+(?:\.\d+)?)\s*[%％]/i],
    ['ubi', /(?:UBI|基本收入)[^\d]{0,20}(\d[\d,]*(?:\.\d+)?)/i]
  ];
  for(const [key,re] of patterns){const m=question.match(re);if(m){p[key]=Number(m[1].replaceAll(',',''));matched.push(key);}}
  if(/productivity doubles|生产率翻倍|生产力翻倍/i.test(question)){p.productivity=100;matched.push('productivity');}
  if(/adoption slows|slow adoption|采用放缓|缓慢采用/i.test(question)){p.speed=5;matched.push('speed');}
  // Chinese often places the number before the noun or verb.
  for(const [key,re] of [['substitution',/(\d+(?:\.\d+)?)\s*[%％].{0,18}(?:自动化|替代)/],['tax',/(\d+(?:\.\d+)?)\s*[%％].{0,8}(?:税)/],['ubi',/(\d[\d,]*)\s*(?:美元|元).{0,10}(?:UBI|基本收入)/i]] as [keyof Params,RegExp][]){const m=question.match(re);if(m&&!matched.includes(key)){p[key]=Number(m[1].replaceAll(',',''));matched.push(key);}}
  const clipped=controls.some(c=>p[c.key]<c.min||p[c.key]>c.max);
  for(const c of controls)p[c.key]=Math.min(c.max,Math.max(c.min,p[c.key]));
  return {params:p,matched,clipped};
}

export type SharedScenario={v:2;lang:'en'|'zh';params:Params;question:string};
export function decodeScenario(hash:string): SharedScenario|null {
  try {const x=JSON.parse(decodeURIComponent(hash.replace(/^#scenario=/,'')));
    if(x.v!==2||!['en','zh'].includes(x.lang)||typeof x.question!=='string'||x.question.length>600)return null;
    for(const c of controls)if(typeof x.params?.[c.key]!=='number'||!Number.isFinite(x.params[c.key])||x.params[c.key]<c.min||x.params[c.key]>c.max)return null;
    return {v:2,lang:x.lang,question:x.question,params:Object.fromEntries(controls.map(c=>[c.key,x.params[c.key]])) as Params};
  }catch{return null;}
}


