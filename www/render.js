/* ================= 红色警戒 · 渲染（高清重制版） ================= */
'use strict';
// 基准缩放：原设计基于 TILE=24，现 TILE=40 → 所有细节放大 US 倍
const US=TILE/24;
// 地形色板（红警2暖色调）
const TC={
  [TG]:['#4f7a3a','#4c7738','#54823e','#4a7336'],   // 草地
  [TD]:['#6a5a3a','#665636','#6e5e3e','#635434'],   // 泥地
  [TS]:['#c0a86a','#bca464','#c5ad6f','#b8a060'],   // 沙地
  [TW]:['#2f5d8a','#2b5783','#326392','#28527d'],   // 水面
  [TT]:['#2e5a2e','#2a552a','#326032','#275227'],   // 森林
  [TR]:['#5a5a5a','#565656','#5e5e5e','#535353']    // 岩石
};
function hash(x,y){ const n=Math.sin(x*127.1+y*311.7)*43758.5453; return n-Math.floor(n); }

function drawTerrain(){
  const sx=Math.max(0,Math.floor(cam.x/TILE)), sy=Math.max(0,Math.floor(cam.y/TILE));
  const ex=Math.min(COLS,Math.ceil((cam.x+cam.vw/cam.z)/TILE)), ey=Math.min(ROWS,Math.ceil((cam.y+cam.vh/cam.z)/TILE));
  for(let y=sy;y<ey;y++)for(let x=sx;x<ex;x++){
    const t=terrain[y][x], px=x*TILE, py=y*TILE;
    const pal=TC[t], c=pal[(Math.floor(hash(x,y)*4)+ (t===TW&&Math.floor(frame/60)%2?2:0))%4];
    ctx.fillStyle=c; ctx.fillRect(px,py,TILE,TILE);
    // 草地纹理：草叶
    if(t===TG){
      if(hash(x*2.3,y*1.7)>.55){
        ctx.fillStyle='rgba(255,255,200,.08)';
        ctx.fillRect(px+hash(x,y)*26,py+hash(y,x)*26,7,3);
      }
      if(hash(x*5.1,y*3.3)>.72){
        ctx.fillStyle='rgba(120,200,90,.35)';
        ctx.beginPath(); ctx.arc(px+8+hash(x,y)*24, py+10+hash(y,x)*20, 2.5, 0, 6.283); ctx.fill();
      }
    }
    if(t===TS&&hash(x,y)>.6){
      ctx.fillStyle='rgba(255,255,255,.06)'; ctx.fillRect(px+hash(x*3,y)*20,py+hash(y*3,x)*20,5,3);
    }
    if(t===TW){
      ctx.fillStyle='rgba(255,255,255,'+(0.05+Math.sin(frame*.03+x*1.3+y)*.03)+')';
      ctx.beginPath(); ctx.arc(px+12+Math.sin(frame*.02+x)*6, py+12+Math.cos(frame*.02+y)*6, 4.5, 0, 6.283); ctx.fill();
    }
    if(t===TT){
      ctx.fillStyle='#1f451f'; ctx.beginPath(); ctx.arc(px+10,py+10,9,0,6.283); ctx.fill();
      ctx.fillStyle='#3a703a'; ctx.beginPath(); ctx.arc(px+23,py+16,10,0,6.283); ctx.fill();
      ctx.fillStyle='#2c5c2c'; ctx.beginPath(); ctx.arc(px+30,py+26,7,0,6.283); ctx.fill();
    }
    if(t===TR){
      ctx.fillStyle='#4a4a4a'; ctx.beginPath();
      ctx.moveTo(px+4,py+27); ctx.lineTo(px+15,py+7); ctx.lineTo(px+26,py+27); ctx.closePath(); ctx.fill();
      ctx.fillStyle='#666'; ctx.beginPath();
      ctx.moveTo(px+20,py+30); ctx.lineTo(px+29,py+13); ctx.lineTo(px+37,py+30); ctx.closePath(); ctx.fill();
      ctx.fillStyle='rgba(255,255,255,.06)'; ctx.fillRect(px+10,py+10,4,8);
    }
  }
}

// ---------- 宝石矿（红警标志性红色晶体） ----------
function drawGems(){
  for(const g of GEMS){
    if(g.amount<=0) continue;
    const px=g.x*TILE+TILE/2, py=g.y*TILE+TILE/2;
    const pulse=.5+Math.sin(frame*.05+g.x)*.5;
    // 光晕
    ctx.fillStyle='rgba(255,80,80,'+(0.12+pulse*.07)+')';
    ctx.beginPath(); ctx.arc(px,py,TILE*.75+pulse*6,0,6.283); ctx.fill();
    // 三颗晶体（内部按基准坐标放大）
    drawGem(px-15,py+13,10,0);
    drawGem(px+13,py+15,8,.4);
    drawGem(px,py-3,13,-.2);
    // 储量
    ctx.fillStyle='rgba(255,130,130,.95)';
    ctx.font='bold 13px sans-serif'; ctx.textAlign='center';
    ctx.fillText(Math.round(g.amount), px, py+TILE+10);
  }
}
function drawGem(x,y,s,rot){
  ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(US,US);
  const g=ctx.createLinearGradient(-s,0,s,0);
  g.addColorStop(0,'#ff5a5a'); g.addColorStop(.5,'#ff9d9d'); g.addColorStop(1,'#c22');
  ctx.fillStyle=g;
  ctx.beginPath(); ctx.moveTo(0,-s); ctx.lineTo(s*.6,0); ctx.lineTo(0,s); ctx.lineTo(-s*.6,0); ctx.closePath(); ctx.fill();
  ctx.strokeStyle='rgba(255,255,255,.55)'; ctx.lineWidth=1.2;
  ctx.beginPath(); ctx.moveTo(0,-s*.6); ctx.lineTo(0,s*.6); ctx.stroke();
  ctx.fillStyle='rgba(255,255,255,.35)';
  ctx.beginPath(); ctx.moveTo(-s*.25,-s*.4); ctx.lineTo(s*.25,-s*.4); ctx.lineTo(0,-s*.85); ctx.closePath(); ctx.fill();
  ctx.restore();
}

// ---------- 建筑 ----------
function drawBuildings(){
  for(const b of buildings){
    const px=b.x*TILE, py=b.y*TILE, sz=b.sz*TILE;
    // 阴影（世界坐标）
    ctx.fillStyle='rgba(0,0,0,.35)';
    ctx.fillRect(px+6,py+6,sz,sz);
    // 主体（基准坐标系，自动放大）
    ctx.save();
    ctx.translate(px,py);
    ctx.scale(US,US);
    const w=b.sz*24; // 基准尺寸
    if(b.t==='hq'){
      const g=ctx.createLinearGradient(0,0,0,w);
      g.addColorStop(0,b.o==='player'?'#3a6ab8':'#b83a3a');
      g.addColorStop(1,b.o==='player'?'#22447a':'#7a2222');
      ctx.fillStyle=g; ctx.fillRect(0,0,w,w);
      ctx.strokeStyle='rgba(255,255,255,.4)'; ctx.lineWidth=2.5; ctx.strokeRect(2,2,w-4,w-4);
      // 屋顶线条
      ctx.strokeStyle='rgba(255,255,255,.18)'; ctx.lineWidth=1.5;
      ctx.beginPath(); ctx.moveTo(0,w*.35); ctx.lineTo(w,w*.35); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(w*.35,0); ctx.lineTo(w*.35,w); ctx.stroke();
      // 大门
      ctx.fillStyle='#1a1a2a'; ctx.fillRect(w/2-13, w-24, 26, 24);
      ctx.fillStyle='rgba(255,211,77,.8)'; ctx.fillRect(w/2-5, w-18, 5, 15);
      // 旗帜（飘动）
      const fy=4+Math.sin(frame*.06)*4;
      ctx.strokeStyle='#999'; ctx.lineWidth=2.5;
      ctx.beginPath(); ctx.moveTo(w-8,4); ctx.lineTo(w-8,fy-16); ctx.stroke();
      ctx.fillStyle=b.o==='player'?'#4a9dff':'#ff4a4a';
      ctx.beginPath(); ctx.moveTo(w-8,fy-16); ctx.lineTo(w+22,fy-10); ctx.lineTo(w-8,fy-4); ctx.closePath(); ctx.fill();
      // 雷达
      ctx.strokeStyle='rgba(255,255,255,.5)'; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(22,22,16,0,6.283); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(22,22); ctx.lineTo(22+Math.cos(frame*.04)*16,22+Math.sin(frame*.04)*16); ctx.stroke();
      ctx.fillStyle='rgba(255,255,255,.3)'; ctx.beginPath(); ctx.arc(22,22,4,0,6.283); ctx.fill();
    }else if(b.t==='barracks'){
      const g=ctx.createLinearGradient(0,0,0,w);
      g.addColorStop(0,'#5a4a3a'); g.addColorStop(1,'#3a3028');
      ctx.fillStyle=g; ctx.fillRect(0,0,w,w);
      ctx.strokeStyle='rgba(255,255,255,.3)'; ctx.lineWidth=2; ctx.strokeRect(2,2,w-4,w-4);
      // 大门
      ctx.fillStyle='#222018'; ctx.fillRect(w/2-15,w-22,30,22);
      ctx.fillStyle='rgba(255,211,77,.4)'; ctx.fillRect(w/2-15,w-22,30,3);
      // 沙袋
      ctx.fillStyle='#8a7a5a'; ctx.fillRect(6,w-12,w-12,9);
      ctx.fillStyle='rgba(0,0,0,.25)';
      for(let i=0;i<4;i++) ctx.fillRect(12+i*(w-24)/3,w-12,6,9);
      // 灯
      ctx.fillStyle='rgba(255,211,77,'+(0.5+Math.sin(frame*.1)*.5)+')';
      ctx.beginPath(); ctx.arc(12,12,5,0,6.283); ctx.fill();
    }else if(b.t==='tower'){
      const g=ctx.createLinearGradient(0,0,0,w);
      g.addColorStop(0,'#6a6a6a'); g.addColorStop(1,'#3a3a3a');
      ctx.fillStyle=g; ctx.fillRect(0,0,w,w);
      ctx.strokeStyle='rgba(255,255,255,.28)'; ctx.lineWidth=2; ctx.strokeRect(2,2,w-4,w-4);
      // 底座装饰
      ctx.fillStyle='rgba(255,255,255,.12)'; ctx.fillRect(6,w-14,w-12,8);
      ctx.fillStyle='rgba(0,0,0,.2)'; ctx.fillRect(6,w-14,w-12,3);
      // 旋转炮管（对准最近的敌人）
      let ang=frame*.02;
      const enemySide=b.o==='player'?'ai':'player';
      let near=null, nd=7.5;
      for(const u of units){ if(u.o!==enemySide)continue; const d=Math.abs(u.x-(b.x+.5))+Math.abs(u.y-(b.y+.5)); if(d<nd){nd=d;near=u;} }
      if(near) ang=Math.atan2(near.y-(b.y+.5), near.x-(b.x+.5));
      ctx.save(); ctx.translate(w/2,w/2); ctx.rotate(ang);
      ctx.fillStyle='#222'; ctx.fillRect(-8,-6,w*.75,12);
      ctx.fillStyle='#999'; ctx.beginPath(); ctx.arc(0,0,11,0,6.283); ctx.fill();
      ctx.fillStyle='#555'; ctx.beginPath(); ctx.arc(0,0,7,0,6.283); ctx.fill();
      ctx.fillStyle='rgba(255,211,77,.5)'; ctx.beginPath(); ctx.arc(0,0,3,0,6.283); ctx.fill();
      ctx.restore();
    }else if(b.t==='factory'){
      const g=ctx.createLinearGradient(0,0,0,w);
      g.addColorStop(0,'#4a3a6a'); g.addColorStop(1,'#2a203e');
      ctx.fillStyle=g; ctx.fillRect(0,0,w,w);
      ctx.strokeStyle='rgba(255,255,255,.3)'; ctx.lineWidth=2; ctx.strokeRect(2,2,w-4,w-4);
      // 烟囱 + 烟雾
      ctx.fillStyle='#555'; ctx.fillRect(12,-14,12,18);
      ctx.fillStyle='rgba(180,180,180,'+(.4+Math.sin(frame*.05)*.15)+')';
      ctx.beginPath(); ctx.arc(18,-20+Math.sin(frame*.05)*4,8+Math.sin(frame*.04)*3,0,6.283); ctx.fill();
      ctx.fillStyle='rgba(200,200,200,.2)';
      ctx.beginPath(); ctx.arc(18+Math.sin(frame*.03)*8,-30,10,0,6.283); ctx.fill();
      // 传送带
      ctx.fillStyle='rgba(255,255,255,.12)';
      ctx.fillRect(6,w-12,w-12,8);
      ctx.fillStyle='rgba(255,255,255,.3)';
      for(let i=0;i<3;i++) ctx.fillRect(10+((i*16+frame)% (w-20)),w-10,6,4);
      // 灯
      ctx.fillStyle='rgba(255,120,80,'+(0.5+Math.sin(frame*.08)*.5)+')';
      ctx.beginPath(); ctx.arc(w-12,12,5,0,6.283); ctx.fill();
    }
    ctx.restore();
    // 血条（世界坐标）
    const hp=b.hp/b.mhp;
    if(hp<1){
      ctx.fillStyle='rgba(0,0,0,.7)'; ctx.fillRect(px,py-12,sz,6);
      ctx.fillStyle=hp>.5?'#6ee87a':hp>.25?'#ffd34d':'#ff5a5a';
      ctx.fillRect(px,py-12,sz*hp,6);
    }
    // 建造中
    if(b.bt>0){ ctx.fillStyle='rgba(255,211,77,.12)'; ctx.fillRect(px,py,sz,sz); b.bt--; }
  }
}

// ---------- 单位 ----------
function drawUnits(){
  for(const u of units){
    const px=u.x*TILE+TILE/2, py=u.y*TILE+TILE/2;
    const isP=u.o==='player', isS=selIds.has(u.id);
    // 选中圈 + 血条（世界坐标）
    if(isS){
      ctx.strokeStyle='rgba(111,216,255,'+(0.5+Math.sin(frame*.1)*.25)+')';
      ctx.lineWidth=2.5;
      ctx.beginPath(); ctx.arc(px,py,14*US,0,6.283); ctx.stroke();
      const hpr=u.hp/u.mhp;
      ctx.fillStyle='rgba(0,0,0,.7)'; ctx.fillRect(px-14*US,py-22*US,28*US,5*US);
      ctx.fillStyle=hpr>.5?'#6ee87a':hpr>.25?'#ffd34d':'#ff5a5a';
      ctx.fillRect(px-14*US,py-22*US,28*US*hpr,5*US);
    }
    ctx.save(); ctx.translate(px,py); ctx.rotate(u.face); ctx.scale(US,US);
    const cMain=isP?'#3a7ad0':'#d03a3a';
    const cDark=isP?'#24508f':'#8f2424';
    const cLight=isP?'#6fa8e8':'#e86f6f';
    if(u.tp==='worker'){
      // 矿工：身体+安全帽+工具+随身金袋
      ctx.fillStyle=cMain; ctx.beginPath(); ctx.arc(0,0,9,0,6.283); ctx.fill();
      ctx.fillStyle=cDark; ctx.beginPath(); ctx.arc(0,0,6,0,6.283); ctx.fill();
      ctx.fillStyle='#ffd34d'; ctx.fillRect(-8,-7,16,5); // 安全帽
      ctx.fillStyle='#ff9d3d'; ctx.fillRect(-5,-10,4,3);
      ctx.fillStyle='#e8a030'; ctx.beginPath(); ctx.arc(0,-9,3.5,0,6.283); ctx.fill();
      // 矿镐
      ctx.strokeStyle='#8a6a3a'; ctx.lineWidth=3;
      ctx.beginPath(); ctx.moveTo(7,5); ctx.lineTo(16,-5); ctx.stroke();
      ctx.fillStyle='#bbb'; ctx.beginPath(); ctx.arc(16,-5,4,0,6.283); ctx.fill();
      if(u.gc>0){ ctx.fillStyle='#ffd34d'; ctx.beginPath(); ctx.arc(0,-14,5+Math.sin(frame*.2)*1.5,0,6.283); ctx.fill(); }
    }else if(u.tp==='soldier'){
      // 士兵：身体+头盔+步枪
      ctx.fillStyle=cMain; ctx.beginPath(); ctx.arc(0,0,8,0,6.283); ctx.fill();
      ctx.fillStyle=cDark; ctx.beginPath(); ctx.arc(0,0,5,0,6.283); ctx.fill();
      ctx.fillStyle='#2a4a2a'; ctx.beginPath(); ctx.arc(0,-4,6,Math.PI,0); ctx.fill();
      ctx.fillStyle='#3a6a3a'; ctx.fillRect(-6,-5,12,2);
      ctx.strokeStyle='#333'; ctx.lineWidth=3;
      ctx.beginPath(); ctx.moveTo(6,-3); ctx.lineTo(18,-3); ctx.stroke();
      ctx.fillStyle='#666'; ctx.fillRect(14,-6,4,5);
    }else if(u.tp==='rocket'){
      // 火箭兵：身体+头盔+火箭筒
      ctx.fillStyle=cMain; ctx.beginPath(); ctx.arc(0,0,8,0,6.283); ctx.fill();
      ctx.fillStyle=cDark; ctx.beginPath(); ctx.arc(0,0,5,0,6.283); ctx.fill();
      ctx.fillStyle='#2a3a5a'; ctx.beginPath(); ctx.arc(0,-4,6,Math.PI,0); ctx.fill();
      ctx.strokeStyle='#4a6a3a'; ctx.lineWidth=5;
      ctx.beginPath(); ctx.moveTo(6,-2); ctx.lineTo(19,-2); ctx.stroke();
      ctx.fillStyle='#ff5a2a'; ctx.beginPath(); ctx.arc(19,-2,4.5,0,6.283); ctx.fill();
      ctx.fillStyle='rgba(255,90,42,.3)'; ctx.beginPath(); ctx.arc(19,-2,7,0,6.283); ctx.fill();
    }else if(u.tp==='tank'){
      // 坦克：履带+车身+炮塔+炮管
      ctx.fillStyle='#242424'; ctx.fillRect(-13,-11,26,22); // 履带底盘
      ctx.fillStyle='#4a4a4a';
      for(let i=0;i<5;i++){ ctx.beginPath(); ctx.arc(-10+i*5,-10,2.8,0,6.283); ctx.fill(); }
      for(let i=0;i<5;i++){ ctx.beginPath(); ctx.arc(-10+i*5,10,2.8,0,6.283); ctx.fill(); }
      ctx.fillStyle=cMain; ctx.fillRect(-8,-8,16,16); // 车身
      ctx.fillStyle=cDark; ctx.fillRect(-5,-7,9,7);
      ctx.fillStyle=cLight; ctx.beginPath(); ctx.arc(0,0,7.5,0,6.283); ctx.fill(); // 炮塔
      ctx.fillStyle=cDark; ctx.beginPath(); ctx.arc(0,0,5,0,6.283); ctx.fill();
      ctx.fillStyle='rgba(255,255,255,.25)'; ctx.beginPath(); ctx.arc(-2,-2,2,0,6.283); ctx.fill();
      // 炮管
      ctx.fillStyle='#333'; ctx.fillRect(0,-3,23,6);
      ctx.fillStyle='#666'; ctx.fillRect(21,-4,4,8);
    }
    ctx.restore();
  }
}

// ---------- 粒子 / 飘字 ----------
function drawParticles(){
  for(const p of particles){
    ctx.globalAlpha=Math.max(0,p.life/p.ml);
    ctx.fillStyle=p.c;
    ctx.beginPath(); ctx.arc(p.x,p.y,Math.max(.5,p.s*(p.life/p.ml)),0,6.283); ctx.fill();
  }
  ctx.globalAlpha=1;
  ctx.font='bold 15px "Microsoft YaHei"';
  ctx.textAlign='center';
  for(const f of floats){
    ctx.globalAlpha=Math.max(0,f.life/f.ml);
    ctx.fillStyle=f.c||'#fff';
    ctx.fillText(f.txt, f.x, f.y);
  }
  ctx.globalAlpha=1;
}

// ---------- 小地图 ----------
function drawMini(){
  mCtx.fillStyle='#0a0f18'; mCtx.fillRect(0,0,mn.width,mn.height);
  const sx=mn.width/COLS, sy=mn.height/ROWS;
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){
    const t=terrain[y][x];
    mCtx.fillStyle = t===TW?'#1a3a5a': t===TT?'#1a3a1a': t===TR?'#3a3a3a': t===TS?'#5a4a2a':'#2a4a2a';
    mCtx.fillRect(x*sx,y*sy,sx+0.5,sy+0.5);
  }
  for(const g of GEMS){ if(g.amount<=0)continue; mCtx.fillStyle='#ff5a5a'; mCtx.fillRect(g.x*sx,g.y*sy,sx*1.4,sy*1.4); }
  for(const b of buildings){ mCtx.fillStyle=b.o==='player'?'#4a9dff':'#ff4a4a'; mCtx.fillRect(b.x*sx,b.y*sy,b.sz*sx,b.sz*sy); }
  for(const u of units){ mCtx.fillStyle=u.o==='player'?'#6ee87a':'#ff7a6b'; mCtx.fillRect(u.x*sx,u.y*sy,Math.max(1.5,sx*1.2),Math.max(1.5,sy*1.2)); }
  // 视口框
  mCtx.strokeStyle='rgba(255,255,255,.75)'; mCtx.lineWidth=1.2;
  mCtx.strokeRect(cam.x/TILE*sx, cam.y/TILE*sy, cam.vw/(cam.z*TILE)*sx, cam.vh/(cam.z*TILE)*sy);
}

// ---------- 主绘制 ----------
function drawAll(){
  ctx.setTransform(DPR,0,0,DPR,0,0);
  ctx.clearRect(0,0,cam.vw,cam.vh);
  ctx.save();
  ctx.translate(-cam.x*cam.z, -cam.y*cam.z);
  ctx.scale(cam.z,cam.z);
  drawTerrain();
  drawGems();
  drawBuildings();
  drawUnits();
  drawParticles();
  ctx.restore();
  drawMini();
}
