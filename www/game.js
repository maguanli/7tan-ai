/* ================= 红色警戒 · 核心逻辑 ================= */
'use strict';
// ---------- 全局 ----------
const COLS=56, ROWS=38, TILE=40;
const W=COLS*TILE, H=ROWS*TILE;
const main=document.getElementById('main'), ctx=main.getContext('2d');
const mn=document.getElementById('mn'), mCtx=mn.getContext('2d');
mn.width=224; mn.height=152;
let cam={x:0,y:0,z:1.15,tz:1.15,vw:0,vh:0};
const keys={};
let frame=0, gameOver=false, killCount=0;
let gold=1000, popMax=50, aiGold=1000, aiPopMax=60;
let units=[], buildings=[], GEMS=[], particles=[], floats=[];
let selIds=new Set(), nextId=1;
const pathCache=new Map();

// ---------- 地形 ----------
const TG=0,TD=1,TS=2,TW=3,TT=4,TR=5;
let terrain=[];
function genTerrain(){
  terrain=[];
  for(let y=0;y<ROWS;y++){
    terrain[y]=[];
    for(let x=0;x<COLS;x++){
      let r=Math.random();
      terrain[y][x]= r<.025?TW : r<.05?TT : r<.065?TR : r<.11?TD : r<.14?TS : TG;
    }
  }
  // 双方基地周围清空
  for(let dy=-4;dy<=4;dy++)for(let dx=-4;dx<=4;dx++){
    if(3+dx>=0&&3+dx<COLS&&5+dy>=0&&5+dy<ROWS)terrain[5+dy][3+dx]=TG;
    if(COLS-6+dx>=0&&COLS-6+dx<COLS&&ROWS-7+dy>=0&&ROWS-7+dy<ROWS)terrain[ROWS-7+dy][COLS-6+dx]=TG;
  }
}
function tileWalk(x,y){ if(x<0||x>=COLS||y<0||y>=ROWS)return false; const t=terrain[y][x]; return t!==TW&&t!==TT; }
function tileBlock(x,y){ if(x<0||x>=COLS||y<0||y>=ROWS)return true;  const t=terrain[y][x]; return t===TW||t===TT||t===TR; }
function bAt(x,y,o){ for(const b of buildings) if(b.o===o && Math.abs(b.x-x)<1.2&&Math.abs(b.y-y)<1.2) return b; return null; }
function wAt(x,y,o){ for(const u of units) if(u.o===o && Math.abs(u.x-x)<.8&&Math.abs(u.y-y)<.8) return u; return null; }

// ---------- BFS 寻路（8方向+对角修正） ----------
function findPath(sx,sy,ex,ey){
  const si=Math.round(sx),sj=Math.round(sy),ei=Math.round(ex),ej=Math.round(ey);
  if(si===ei&&sj===ej) return [{x:ex,y:ey}];
  const key=si+','+sj+'-'+ei+','+ej;
  if(pathCache.has(key)) return pathCache.get(key);
  const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
  const q=[[si,sj,[{x:si,y:sj}]]], vis=new Set([si+','+sj]);
  let head=0;
  while(head<q.length){
    const [cx,cy,path]=q[head++];
    for(const[dx,dy]of dirs){
      const nx=cx+dx, ny=cy+dy;
      if(nx<0||nx>=COLS||ny<0||ny>=ROWS) continue;
      const nk=nx+','+ny; if(vis.has(nk)) continue;
      if(dx!==0&&dy!==0){ if(!tileWalk(cx+dx,cy)||!tileWalk(cx,cy+dy)) continue; }
      if(!tileWalk(nx,ny)) continue;
      if(bAt(nx,ny,'player')||bAt(nx,ny,'ai')){ if(!(nx===ei&&ny===ej)) continue; }
      const np=path.concat([{x:nx,y:ny}]);
      if(nx===ei&&ny===ej){ pathCache.set(key,np); if(pathCache.size>600)pathCache.clear(); return np; }
      vis.add(nk); q.push([nx,ny,np]);
    }
  }
  pathCache.set(key,null); if(pathCache.size>600)pathCache.clear();
  return null;
}

// ---------- 宝石矿 ----------
function genGems(){
  GEMS=[];
  [[11,9],[23,7],[16,16],[30,13],[8,29],[26,26],[36,30],[20,32],[40,10],[45,22]].forEach(([x,y])=>{
    // 强制矿点及周围为草地，保证可达
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      if(x+dx>=0&&x+dx<COLS&&y+dy>=0&&y+dy<ROWS) terrain[y+dy][x+dx]=TG;
    }
    GEMS.push({x,y,amount:700+Math.random()*500, max:1200});
  });
}
function nearestGem(ux,uy,o){
  let best=null,bd=1e9;
  for(const g of GEMS){
    if(g.amount<=0) continue;
    const d=Math.abs(ux-g.x)+Math.abs(uy-g.y);
    if(d<bd){bd=d;best=g;}
  }
  return best;
}

// ---------- 建筑 ----------
const BD={
  hq:{hp:1000,sz:3,nm:'基地'},
  barracks:{hp:500,sz:2,nm:'兵营'},
  tower:{hp:400,sz:2,nm:'防御塔'},
  factory:{hp:600,sz:2,nm:'坦克工厂'}
};
function addB(type,x,y,o){
  const d=BD[type];
  buildings.push({id:nextId++,t:type,x,y,o,hp:d.hp,mhp:d.hp,sz:d.sz,bt:type==='hq'?0:45});
}
function findB(o,t){ return buildings.find(b=>b.o===o&&b.t===t); }
function nearB(o,t,x,y){
  let best=null,bd=1e9;
  for(const b of buildings){ if(b.o!==o||b.t!==t)continue; const d=Math.abs(b.x-x)+Math.abs(b.y-y); if(d<bd){bd=d;best=b;} }
  return best;
}

// ---------- 单位 ----------
const UD={
  worker: {hp:70, spd:.16, atk:3,  rng:1.2, nm:'矿工',   cost:50,  pp:1, v:6,  carry:30},
  soldier:{hp:110,spd:.11, atk:15, rng:3.5, nm:'士兵',   cost:100, pp:1, v:7},
  rocket: {hp:85, spd:.09, atk:30, rng:5,   nm:'火箭兵', cost:150, pp:1, v:7},
  tank:   {hp:320,spd:.07, atk:45, rng:4.5, nm:'坦克',   cost:250, pp:2, v:8}
};
function addU(type,x,y,o){
  const d=UD[type];
  units.push({
    id:nextId++, tp:type, x,y, o,
    hp:d.hp, mhp:d.hp, spd:d.spd, atk:d.atk, rng:d.rng*TILE,
    nm:d.nm, cost:d.cost, pp:d.pp, v:d.v*TILE,
    tx:null,ty:null,tid:null, gc:0, mining:false, mt:null,
    acd:0, atk:false, stuck:0, pi:0, path:null, face:Math.PI, born:frame
  });
}
function popOf(o){ return units.reduce((s,u)=>s+(u.o===o?u.pp:0),0); }

// ---------- 日志 / 飘字 ----------
function log(m,c){
  const el=document.getElementById('lg');
  el.innerHTML='<div class="'+(c||'')+'">'+m+'</div>'+el.innerHTML;
  while(el.children.length>50) el.removeChild(el.lastChild);
}
function floatTxt(x,y,txt,c){
  floats.push({x,y,txt,c,life:55,ml:55});
}

// ---------- 命令 ----------
function cmd(a){
  if(gameOver) return;
  if(a==='bB') build('barracks',200);
  else if(a==='bT') build('tower',150);
  else if(a==='bF') build('factory',350);
  else if(a==='tW') train('worker');
  else if(a==='tS') train('soldier');
  else if(a==='tR') train('rocket');
  else if(a==='tK') train('tank');
  else if(a==='aS'){ selIds.clear(); for(const u of units) if(u.o==='player'&&u.tp!=='worker') selIds.add(u.id); log('🎖 已选中 '+selIds.size+' 个战斗单位','i'); }
  else if(a==='halt'){ for(const u of units) if(selIds.has(u.id)){ u.tx=null;u.ty=null;u.tid=null;u.atk=false;u.path=null; } log('🛑 已停止','i'); }
}
function build(type,cost){
  if(gold<cost){ log('💰 资金不足！','b'); return; }
  if(type==='barracks'&&findB('player','barracks')){ log('⚠ 已有兵营','i'); return; }
  if(type==='factory'&&findB('player','factory')){ log('⚠ 已有坦克工厂','i'); return; }
  if(type==='factory'&&!findB('player','barracks')){ log('⚠ 需要先建兵营','b'); return; }
  if(type==='tower'&&!findB('player','barracks')&&!findB('player','factory')){ log('⚠ 需要先建兵营或工厂','b'); return; }
  const hq=findB('player','hq'); if(!hq) return;
  const spots=[[3,0],[-3,0],[0,3],[0,-3],[3,3],[-3,3],[3,-3],[-3,-3],[4,0],[-4,0],[0,4],[0,-4]];
  for(const[dx,dy]of spots){
    const bx=hq.x+dx, by=hq.y+dy;
    if(!tileBlock(bx,by) && !bAt(bx,by,'player') && !bAt(bx,by,'ai')){
      gold-=cost;
      addB(type,bx,by,'player');
      if(type==='barracks') popMax+=20;
      log('🏗 '+(type==='barracks'?'兵营':type==='tower'?'防御塔':'坦克工厂')+' 建造完成','g');
      return;
    }
  }
  log('🏗 基地周围没有空位！','b');
}
function train(type){
  const d=UD[type];
  if(popOf('player')+d.pp>popMax){ log('👥 人口不足！','b'); return; }
  if(gold<d.cost){ log('💰 资金不足！','b'); return; }
  let sp = type==='tank' ? findB('player','factory') : findB('player','barracks');
  if(type==='tank'&&!sp) sp=findB('player','factory');
  if(!sp && type!=='worker'){ log('⚠ 需要兵营（矿工无需建筑）','b'); return; }
  let bx,by;
  if(type==='worker'){
    const hq=findB('player','hq'); if(!hq) return;
    bx=hq.x; by=hq.y+1.5;
  }else{ bx=sp.x; by=sp.y+1.2; }
  gold-=d.cost;
  addU(type,bx+ (Math.random()*.6-.3), by, 'player');
  log('🎖 训练了 '+d.nm,'g');
}

// ---------- 粒子 ----------
function spawnP(x,y,vx,vy,life,color,sz){ particles.push({x,y,vx,vy,life,ml:life,c:color,s:sz*(TILE/24)}); }
function boom(x,y){
  for(let i=0;i<14;i++){ const a=Math.random()*6.283, s=Math.random()*2.4+1;
    spawnP(x,y,Math.cos(a)*s,Math.sin(a)*s,22+Math.random()*12,['#ffd34d','#ff8c3a','#ff5a3a','#fff0c0'][~~(Math.random()*4)],2+Math.random()*3); }
  spawnP(x,y,0,-.5,30,'#666',6);
}
function muzzle(x,y,tx,ty){
  const dx=tx-x,dy=ty-y,d=Math.sqrt(dx*dx+dy*dy)||1;
  for(let i=0;i<5;i++){ const s=Math.random()*3+2;
    spawnP(x,y,(dx/d)*s,(dy/d)*s,6+Math.random()*5,['#ffd34d','#ff9d3d','#fff'][~~(Math.random()*3)],2); }
}
function spark(x,y){
  for(let i=0;i<4;i++){ const a=Math.random()*6.283,s=Math.random()*1.6;
    spawnP(x,y,Math.cos(a)*s,Math.sin(a)*s-.4,14,'#ffd34d',1.6); }
}
function updateP(){
  for(const p of particles){ p.x+=p.vx; p.y+=p.vy; p.vy+=.025; p.life--; }
  particles=particles.filter(p=>p.life>0);
  for(const f of floats){ f.y-=.35; f.life--; }
  floats=floats.filter(f=>f.life>0);
}

// ---------- 工人采矿（核心：自动循环，绝不卡死） ----------
function workerAI(u){
  const CARRY=UD.worker.carry;
  // 1) 带着矿 → 回 HQ
  if(u.gc>=CARRY){
    if(u.tx===null&&u.ty===null){
      const hq=nearB(u.o,'hq',u.x,u.y);
      if(hq){ u.tx=hq.x; u.ty=hq.y; u.path=null; u.pi=0; }
    }
    if(u.tx===null&&u.ty===null) return;
    // 到家 → 卸货
    const hq=nearB(u.o,'hq',u.x,u.y);
    if(hq&&Math.abs(u.x-hq.x)<1.6&&Math.abs(u.y-hq.y)<1.6){
      if(u.o==='player'){ gold+=u.gc; } else { aiGold+=u.gc; }
      floatTxt(hq.x*TILE+TILE/2, hq.y*TILE-6, '+'+(u.o==='player'?u.gc:u.gc), u.o==='player'?'#ffd34d':'#ff7a6b');
      u.gc=0; u.mining=false; u.mt=null;
      u.tx=null; u.ty=null; u.path=null;
      // 立即找下一个矿
      const g=nearestGem(u.x,u.y,u.o);
      if(g){ u.mt=g; u.mining=true; u.tx=g.x; u.ty=g.y; u.path=null; u.pi=0; }
    }
    return;
  }
  // 2) 空手 → 找矿
  if(!u.mining && u.tx===null&&u.ty===null){
    const g=nearestGem(u.x,u.y,u.o);
    if(g){ u.mt=g; u.mining=true; u.tx=g.x; u.ty=g.y; u.path=null; u.pi=0; }
    return;
  }
  // 2.5) 离矿足够近 → 强制清空移动目标开始采矿
  if(u.mining&&u.mt&&(u.tx!==null||u.ty!==null)){
    const g0=u.mt;
    if(g0&&g0.amount>0&&Math.abs(u.x-g0.x)<1.7&&Math.abs(u.y-g0.y)<1.7){
      u.tx=null; u.ty=null; u.path=null; u.pi=0;
    }
  }
  // 3) 到达矿 → 采矿
  if(u.mining&&u.mt&&u.tx===null&&u.ty===null){
    const g=u.mt;
    if(!g||g.amount<=0){
      u.mining=false; u.mt=null;
      const g2=nearestGem(u.x,u.y,u.o);
      if(g2){ u.mt=g2; u.mining=true; u.tx=g2.x; u.ty=g2.y; u.path=null; u.pi=0; }
      return;
    }
    if(Math.abs(u.x-g.x)<1.7&&Math.abs(u.y-g.y)<1.7){
      const take=Math.min(.8, g.amount, CARRY-u.gc);
      g.amount-=take; u.gc+=take;
      if(frame%12===0) spark(u.x*TILE+TILE/2, u.y*TILE+TILE/2);
      if(u.gc>=CARRY){ u.mining=false; u.tx=null;u.ty=null;u.path=null; }
    }else{
      // 没到矿却停了 → 重新寻路
      u.tx=g.x; u.ty=g.y; u.path=null; u.pi=0;
    }
  }
}

// ---------- 战斗（公共） ----------
function combatUnit(u){
  if(u.tp==='worker') return;
  if(u.acd>0) u.acd--;
  // 攻击目标
  if(u.tid){
    const t=units.find(v=>v.id===u.tid);
    if(!t||t.hp<=0){ u.tid=null; u.atk=false; }
    else{
      const d=Math.abs(u.x-t.x)+Math.abs(u.y-t.y);
      if(d<u.rng/TILE){
        if(u.acd<=0){
          t.hp-=u.atk;
          u.acd= u.tp==='tank'?32 : u.tp==='rocket'?26 : u.tp==='soldier'?20 : 20;
          muzzle(u.x*TILE+TILE/2,u.y*TILE+TILE/2,t.x*TILE+TILE/2,t.y*TILE+TILE/2);
          if(t.hp<=0){ boom(t.x*TILE+TILE/2,t.y*TILE+TILE/2);
            if(t.o==='player'){ killCount++; document.getElementById('hKill').textContent=killCount; }
            log((u.o==='player'?'🔵 ':'🔴 ')+u.nm+' 消灭了 '+(t.o==='player'?'你的':'敌军')+t.nm, u.o==='player'?'g':'b');
            if(t.tp==='worker'&&t.o==='player'){ floatTxt(t.x*TILE, t.y*TILE, '矿工阵亡！','#ff7a6b'); }
            u.tid=null; u.atk=false;
          }
        }
      }else{
        u.tx=t.x; u.ty=t.y; u.path=null; u.pi=0; u.atk=true;
      }
    }
  }
  // 自动索敌
  if(!u.tid&&!u.atk){
    let near=null,nd=u.tp==='tank'?8:6;
    for(const p of units){
      if(p.o===u.o||p.tp==='worker') continue;
      const d=Math.abs(u.x-p.x)+Math.abs(u.y-p.y);
      if(d<nd){ nd=d; near=p; }
    }
    if(near){ u.tid=near.id; u.atk=true; }
  }
}

// ---------- 移动（BFS路径+防卡死） ----------
function moveUnit(u){
  if(u.tx===null||u.ty===null||u.tid) return;
  if(!u.path){
    u.path=findPath(u.x,u.y,u.tx,u.ty); u.pi=0;
    // 路径只有起点(目标格=当前格)：直接判定到达
    if(u.path&&u.path.length===1){
      const dx1=u.tx-u.x, dy1=u.ty-u.y;
      if(Math.sqrt(dx1*dx1+dy1*dy1)<=.7){ u.tx=null; u.ty=null; }
      u.path=null; u.pi=0; return;
    }
    if(!u.path){
      u.stuck++;
      const dx3=u.tx-u.x, dy3=u.ty-u.y;
      if(Math.sqrt(dx3*dx3+dy3*dy3)<=1.5){
        // 目标近在咫尺但寻路失败：直接判定到达
        u.tx=null; u.ty=null; u.stuck=0; return;
      }
      if(u.stuck>25){
        // 直线尝试一次
        const dx=u.tx-u.x,dy=u.ty-u.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d>.5){ u.x+=dx/d*u.spd; u.y+=dy/d*u.spd; }
        u.stuck=0; u.path=null;
      }
      return;
    }
  }
  if(u.pi>=u.path.length){
    u.path=null; u.pi=0;
    // 到达终点：清空目标，触发采矿/卸货判定
    const dx2=u.tx-u.x, dy2=u.ty-u.y;
    if(Math.sqrt(dx2*dx2+dy2*dy2)<=.7){ u.tx=null; u.ty=null; }
    return;
  }
  const wp=u.path[u.pi];
  const dx=wp.x-u.x, dy=wp.y-u.y, d=Math.sqrt(dx*dx+dy*dy);
  if(d>.25){
    u.face=Math.atan2(dy,dx);
    const nx=u.x+(dx/d)*u.spd, ny=u.y+(dy/d)*u.spd;
    // 碰撞检测（建筑+单位，宽松）
    let blocked=false;
    if(tileBlock(Math.round(nx),Math.round(ny))) blocked=true;
    for(const b of buildings){
      if(Math.abs(nx-b.x)<1.0&&Math.abs(ny-b.y)<1.0){ blocked=true; break; }
    }
    if(!blocked){
      u.x=nx; u.y=ny; u.stuck=0;
    }else{
      u.stuck++;
      if(u.stuck>12){ u.path=null; u.pi=0; u.stuck=0; }
    }
  }else{
    u.pi++;
    if(u.pi>=u.path.length) u.path=null;
  }
}

// ---------- 主更新 ----------
function update(){
  frame++;
  // 自动生成工人（玩家）——缓解人口不足
  if(frame%450===0){
    const pw=units.filter(u=>u.o==='player'&&u.tp==='worker').length;
    if(pw<8 && popOf('player')+1<=popMax){
      const hq=findB('player','hq');
      if(hq){ addU('worker',hq.x, hq.y+1.5,'player'); log('🏭 基地自动补充了 1 名矿工','i'); }
    }
  }
  // 单位更新
  for(const u of units){
    workerAI(u);
    combatUnit(u);
    moveUnit(u);
  }
  // 死亡清理
  const dead=units.filter(u=>u.hp<=0);
  for(const u of dead){ if(u.tp!=='worker') boom(u.x*TILE+TILE/2,u.y*TILE+TILE/2); }
  units=units.filter(u=>u.hp>0);
  for(const b of buildings){
    if(b.hp<=0){
      boom((b.x+b.sz/2)*TILE,(b.y+b.sz/2)*TILE);
      if(b.t==='hq'){
        gameOver=true;
        const el=document.getElementById('ov');
        document.getElementById('ot').textContent = b.o==='player' ? '基地被摧毁' : '胜利！';
        document.getElementById('om').textContent = b.o==='player' ? '敌军摧毁了你的基地' : '你摧毁了敌军基地！';
        el.classList.add('show');
      }
      log((b.o==='player'?'🔵 ':'🔴 ')+'建筑 '+(b.t==='hq'?'基地':BD[b.t].nm)+' 被摧毁！', 'b');
    }
  }
  buildings=buildings.filter(b=>b.hp>0);
  updateP();
  // 防御塔开火
  for(const b of buildings){
    if(b.t!=='tower') continue;
    const enemySide = b.o==='player' ? 'ai' : 'player';
    let near=null, nd=7.5;
    for(const u of units){
      if(u.o!==enemySide) continue;
      const d=Math.abs(u.x-(b.x+.5))+Math.abs(u.y-(b.y+.5));
      if(d<nd){ nd=d; near=u; }
    }
    if(near&&frame%22===0){
      near.hp-=18;
      muzzle((b.x+.5)*TILE,(b.y+.5)*TILE,near.x*TILE,near.y*TILE);
      if(near.hp<=0) log('💥 防御塔击毁了敌军 '+near.nm,'g');
    }
  }
  runAI();
  syncUI();
}

// ---------- AI ----------
function runAI(){
  if(gameOver) return;
  const au=units.filter(u=>u.o==='ai');
  const aw=au.filter(u=>u.tp==='worker').length;
  const ap=popOf('ai');
  // 训练矿工
  if(aiGold>=50 && aw<8 && ap+1<=aiPopMax && frame%120===0){
    const hq=findB('ai','hq');
    if(hq){ aiGold-=50; addU('worker',hq.x, hq.y+1.5,'ai'); }
  }
  // 建筑
  if(!findB('ai','barracks') && aiGold>=200){
    const hq=findB('ai','hq');
    if(hq){ aiGold-=200; addB('barracks',hq.x+3,hq.y,'ai'); }
  }
  if(!findB('ai','tower') && aiGold>=150 && findB('ai','barracks')){
    const hq=findB('ai','hq');
    if(hq){ aiGold-=150; addB('tower',hq.x-3,hq.y,'ai'); }
  }
  if(!findB('ai','factory') && aiGold>=350 && findB('ai','barracks')){
    const hq=findB('ai','hq');
    if(hq){ aiGold-=350; addB('factory',hq.x+3,hq.y+3,'ai'); }
  }
  // 练兵
  const combat=au.filter(u=>u.tp!=='worker');
  if(findB('ai','barracks') && ap+1<=aiPopMax && frame%160===0){
    if(aiGold>=250 && findB('ai','factory') && combat.length>4 && Math.random()<.5){
      const f=findB('ai','factory'); aiGold-=250; addU('tank',f.x,f.y+1.2,'ai');
    }else if(aiGold>=150 && Math.random()<.5){
      const b=findB('ai','barracks'); aiGold-=150; addU('rocket',b.x,b.y+1.2,'ai');
    }else if(aiGold>=100){
      const b=findB('ai','barracks'); aiGold-=100; addU('soldier',b.x,b.y+1.2,'ai');
    }
  }
  // 进攻
  if(combat.length>=5 && frame%900===0){
    const pHQ=findB('player','hq');
    if(pHQ){
      for(const u of combat){
        u.tx=pHQ.x+Math.random()*5-2.5; u.ty=pHQ.y+Math.random()*5-2.5;
        u.tid=null; u.atk=true; u.path=null; u.pi=0;
      }
      log('🔴 敌军发动进攻！','b');
      floatTxt(pHQ.x*TILE, pHQ.y*TILE-16,'敌军来袭！','#ff7a6b');
    }
  }
}

// ---------- UI 同步 ----------
function syncUI(){
  document.getElementById('hGold').textContent=Math.floor(gold);
  document.getElementById('hPop').textContent=popOf('player')+'/'+popMax;
  const hq=findB('player','hq');
  document.getElementById('hHq').textContent=hq?Math.max(0,Math.round(hq.hp/hq.mhp*100))+'%':'已毁';
  // 按钮可用态
  const can=pr=>gold>=pr;
  document.getElementById('btnBarracks').classList.toggle('off',!can(200));
  document.getElementById('btnTower').classList.toggle('off',!can(150));
  document.getElementById('btnFactory').classList.toggle('off',!can(350));
  document.getElementById('btnWorker').classList.toggle('off',!can(50));
  document.getElementById('btnSoldier').classList.toggle('off',!can(100));
  document.getElementById('btnRocket').classList.toggle('off',!can(150));
  document.getElementById('btnTank').classList.toggle('off',!can(250));
  updateSI();
}

// ---------- 选中信息 ----------
function updateSI(){
  const el=document.getElementById('si');
  const sel=units.filter(u=>selIds.has(u.id));
  if(sel.length===1){
    const u=sel[0];
    const hp=Math.max(0,Math.round(u.hp/u.mhp*100));
    const hc=hp>50?'#6ee87a':hp>25?'#ffd34d':'#ff5a5a';
    let st='待命';
    if(u.tp==='worker') st= u.gc>=UD.worker.carry?'回基地卸货':u.mining?'采矿中 '+Math.round(u.gc)+'/'+UD.worker.carry:'寻找矿脉';
    else if(u.tid) st='交战中';
    else if(u.tx!==null) st='移动中';
    el.innerHTML='<div class="nm '+(u.o==='player'?'blue':'red')+'">'+(u.o==='player'?'🔵 ':'🔴 ')+u.nm+'</div>'+
      '<div>生命 '+Math.round(u.hp)+'/'+u.mhp+'</div>'+
      '<div class="bar"><div style="width:'+hp+'%;background:'+hc+'"></div></div>'+
      '<div>攻击 '+u.atk+' · 射程 '+Math.round(u.rng/TILE)+'格</div>'+
      '<div style="color:#6f7f97">'+st+'</div>';
  }else if(sel.length>1){
    el.innerHTML='<div class="nm blue">已选中 '+sel.length+' 个单位</div><div style="color:#6f7f97">右键下达移动/攻击命令</div>';
  }else{
    el.innerHTML='<div style="color:#5a6a82">点击单位查看详情<br>右键地面移动 · 右键敌军攻击</div>';
  }
}

// ---------- 初始化 ----------
function init(){
  units=[]; buildings=[]; particles=[]; floats=[];
  selIds=new Set(); pathCache.clear();
  gold=1000; aiGold=1000; killCount=0;
  popMax=50; aiPopMax=60;
  gameOver=false; frame=0; nextId=1;
  genTerrain(); genGems();
  // 双方基地
  addB('hq',3,5,'player'); addB('hq',COLS-6,ROWS-7,'ai');
  addB('barracks',6,5,'player'); addB('barracks',COLS-3,ROWS-7,'ai');
  // 初始单位
  for(let i=0;i<6;i++) addU('worker', 3+Math.random()*2, 7+Math.random()*2, 'player');
  for(let i=0;i<6;i++) addU('worker', COLS-6+Math.random()*2, ROWS-5+Math.random()*2, 'ai');
  addU('soldier',4,9,'player'); addU('soldier',COLS-5,ROWS-4,'ai');
  // 相机对准基地
  cam.z=1.15; cam.tz=1.15;
  resizeCanvas();
  cam.x=(3.5*TILE)-cam.vw/(2*cam.z); cam.y=(6*TILE)-cam.vh/(2*cam.z);
  clampCam();
  document.getElementById('lg').innerHTML='';
  document.getElementById('ov').classList.remove('show');
  log('🎮 红色警戒开始！矿工已自动采矿','i');
  log('💡 建兵营→练兵→摧毁敌方基地','i');
}

// ---------- 相机 ----------
let DPR=1;
function resizeCanvas(){
  const r=document.getElementById('gameArea').getBoundingClientRect();
  DPR=window.devicePixelRatio||1;
  cam.vw=r.width; cam.vh=r.height;
  main.width=Math.round(r.width*DPR); main.height=Math.round(r.height*DPR);
  ctx.setTransform(DPR,0,0,DPR,0,0);
}
function clampCam(){
  cam.x=Math.max(0,Math.min(W-cam.vw/cam.z,cam.x));
  cam.y=Math.max(0,Math.min(H-cam.vh/cam.z,cam.y));
}
function s2w(sx,sy){ return{x:sx/cam.z+cam.x, y:sy/cam.z+cam.y}; }

// ---------- 输入 ----------
window.addEventListener('resize',resizeCanvas);
window.addEventListener('keydown',e=>{
  keys[e.key.toLowerCase()]=true;
  if(e.key==='Escape'){ selIds.clear(); updateSI(); }
  if((e.key==='r'||e.key==='R')&&gameOver) init();
  if((e.key==='w'||e.key==='W'||e.key==='ArrowUp')&&gameOver) location.reload();
});
window.addEventListener('keyup',e=>{ keys[e.key.toLowerCase()]=false; });
main.addEventListener('wheel',e=>{
  e.preventDefault();
  const old=cam.z;
  cam.tz=Math.max(.6,Math.min(2.4, cam.tz+(e.deltaY>0?-.09:.09)));
  // 以鼠标为中心缩放
  const r=main.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const wx=cam.x+mx/cam.z, wy=cam.y+my/cam.z;
  cam.x=wx-mx/cam.tz; cam.y=wy-my/cam.tz;
  clampCam();
},{passive:false});
// 左键：单击选择 / 框选
let dragS=null,dragE=null;
main.addEventListener('mousedown',e=>{
  if(e.button===0){ dragS={x:e.clientX,y:e.clientY}; dragE=null; }
});
main.addEventListener('mousemove',e=>{ if(dragS) dragE={x:e.clientX,y:e.clientY}; });
main.addEventListener('mouseup',e=>{
  if(e.button!==0) return;
  const r=main.getBoundingClientRect();
  if(dragS&&dragE&&(Math.abs(dragE.x-dragS.x)>8||Math.abs(dragE.y-dragS.y)>8)){
    const x1=Math.min(dragS.x,dragE.x),x2=Math.max(dragS.x,dragE.x);
    const y1=Math.min(dragS.y,dragE.y),y2=Math.max(dragS.y,dragE.y);
    const p1=s2w(x1-r.left,y1-r.top),p2=s2w(x2-r.left,y2-r.top);
    selIds.clear();
    for(const u of units){
      if(u.o!=='player') continue;
      const ux=u.x*TILE+TILE/2, uy=u.y*TILE+TILE/2;
      if(ux>=p1.x&&ux<=p2.x&&uy>=p1.y&&uy<=p2.y) selIds.add(u.id);
    }
    updateSI();
  }else{
    const w=s2w(e.clientX-r.left,e.clientY-r.top);
    const gx=Math.round(w.x/TILE), gy=Math.round(w.y/TILE);
    let found=null;
    for(const u of units){
      if(u.o==='player'&&Math.abs(u.x-gx)<1.3&&Math.abs(u.y-gy)<1.3){ found=u; break; }
    }
    if(found){ if(!e.shiftKey) selIds.clear(); selIds.add(found.id); }
    else selIds.clear();
    updateSI();
  }
  dragS=null; dragE=null;
});
main.addEventListener('dblclick',e=>{
  const r=main.getBoundingClientRect();
  const w=s2w(e.clientX-r.left,e.clientY-r.top);
  const gx=Math.round(w.x/TILE), gy=Math.round(w.y/TILE);
  let tp=null;
  for(const u of units){
    if(u.o==='player'&&Math.abs(u.x-gx)<1.3&&Math.abs(u.y-gy)<1.3){ tp=u.tp; break; }
  }
  if(tp){ selIds.clear(); for(const u of units) if(u.o==='player'&&u.tp===tp) selIds.add(u.id); updateSI(); }
});
// 右键：移动/攻击
main.addEventListener('contextmenu',e=>{
  e.preventDefault();
  if(gameOver) return;
  const r=main.getBoundingClientRect();
  const w=s2w(e.clientX-r.left,e.clientY-r.top);
  const gx=Math.round(w.x/TILE), gy=Math.round(w.y/TILE);
  let eU=null;
  for(const u of units){
    if(u.o==='player') continue;
    if(Math.abs(w.x-(u.x*TILE+TILE/2))<16&&Math.abs(w.y-(u.y*TILE+TILE/2))<16){ eU=u; break; }
  }
  let eB=null;
  if(!eU){
    for(const b of buildings){
      if(b.o==='player') continue;
      const bx=b.x*TILE, by=b.y*TILE, bs=b.sz*TILE;
      if(w.x>=bx&&w.x<=bx+bs&&w.y>=by&&w.y<=by+bs){ eB=b; break; }
    }
  }
  let count=0;
  for(const id of selIds){
    const u=units.find(v=>v.id===id); if(!u) continue;
    if(eU){ u.tid=eU.id; u.tx=null;u.ty=null;u.path=null;u.atk=true; }
    else if(eB){ u.tx=eB.x; u.ty=eB.y; u.tid=null;u.path=null;u.atk=true; }
    else { u.tx=gx; u.ty=gy; u.tid=null;u.path=null;u.atk=false; }
    count++;
  }
  if(count>0) log('📋 '+count+' 个单位 → '+(eU?'攻击 '+eU.nm:eB?'攻击建筑':'移动'),'i');
});
// 小地图
document.getElementById('mw').addEventListener('click',e=>{
  const rect=e.target.getBoundingClientRect();
  const mx=(e.clientX-rect.left)/rect.width*COLS;
  const my=(e.clientY-rect.top)/rect.height*ROWS;
  cam.x=mx*TILE-cam.vw/(2*cam.z); cam.y=my*TILE-cam.vh/(2*cam.z);
  clampCam();
});

// ---------- 主循环 ----------
function gameLoop(){
  if(!gameOver) update();
  // 平滑缩放
  if(Math.abs(cam.z-cam.tz)>.001){ cam.z+=(cam.tz-cam.z)*.12; clampCam(); }
  // WASD 滚动
  const spd=14/cam.z;
  if(keys['w']||keys['arrowup']) cam.y-=spd;
  if(keys['s']||keys['arrowdown']) cam.y+=spd;
  if(keys['a']||keys['arrowleft']) cam.x-=spd;
  if(keys['d']||keys['arrowright']) cam.x+=spd;
  clampCam();
  try{ drawAll(); }catch(e){ console.error('draw:',e); }
  requestAnimationFrame(gameLoop);
}

window.addEventListener('load', function(){ init(); gameLoop(); });
