/** Run the pinned upstream TypeScript with Node 24 native type stripping. */
import { simulate, defaults } from './model.ts';
import { writeFileSync } from 'node:fs';
const cases = [
  {name:'default', params:defaults},
  {name:'augmentation', params:{...defaults,substitution:10,productivity:60,speed:20}},
  {name:'substitution', params:{...defaults,substitution:45,productivity:40,speed:20}},
  {name:'maximum', params:{substitution:60,productivity:100,speed:25,ubi:2000,tax:40}},
  {name:'zero', params:{substitution:0,productivity:0,speed:0,ubi:0,tax:0}}
];
writeFileSync(new URL('./expected.json',import.meta.url), JSON.stringify(cases.map(c=>({...c,rows:simulate(c.params)})),null,2));
console.log('Generated 5 cases x 11 years x 13 fields from upstream TypeScript.');
