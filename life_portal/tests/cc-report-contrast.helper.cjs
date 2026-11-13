// Evaluated in the browser. Check visible text against the backgrounds that can
// actually paint behind it, including inherited WebKit fill and gradients.
module.exports = `(() => {
 const rgba=value=>{const m=value?.match(/rgba?\\(([^)]+)\\)/);if(!m)return null;const n=m[1].split(/[, /]+/).filter(Boolean).map(Number);return [n[0],n[1],n[2],n[3]??1];};
 const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])).concat(1);
 const lum=c=>{const n=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return n[0]*.2126+n[1]*.7152+n[2]*.0722;};
 const ratio=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
 const root=document.querySelector('.cc-report-native'),issues=[];if(!root)return [{text:'Missing report root'}];
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()){
  const node=walker.currentNode,element=node.parentElement,text=node.textContent.trim();
  if(!text||!element||element.closest('script,style,[aria-hidden=true]')||!element.getClientRects().length)continue;
  const style=getComputedStyle(element);if(style.visibility==='hidden'||element.closest(':disabled'))continue;
  let opacity=1,palette=[[255,255,255,1]],ancestors=[];
  for(let p=element;p;p=p.parentElement){ancestors.unshift(p);opacity*=Number(getComputedStyle(p).opacity);}
  if(opacity<.7)continue;
  for(const parent of ancestors){const s=getComputedStyle(parent),bg=rgba(s.backgroundColor);if(bg&&bg[3]>0)palette=palette.map(c=>blend(bg,c));
   if(s.backgroundImage.includes('gradient')){const colors=[...s.backgroundImage.matchAll(/rgba?\\([^)]+\\)/g)].map(m=>rgba(m[0])).filter(Boolean);if(colors.length)palette=colors.flatMap(c=>palette.map(base=>blend(c,base)));}
  }
  const fill=rgba(style.webkitTextFillColor)||rgba(style.color);if(!fill)continue;
  const minimum=Math.min(...palette.map(bg=>ratio(blend(fill,bg),bg))),large=Number.parseFloat(style.fontSize)>=24||(Number.parseFloat(style.fontSize)>=18.66&&Number(style.fontWeight)>=700);
  if(minimum<(large?3:4.5)-.05)issues.push({text:text.slice(0,90),ratio:Number(minimum.toFixed(2)),color:style.color,fill:style.webkitTextFillColor,tag:element.tagName,classes:element.className});
 }
 return issues.slice(0,80);
})()`;
