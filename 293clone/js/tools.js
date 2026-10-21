/* 293查询 仿站 · 工具脚本
 * 说明：本站为前端仿站 Demo。
 * - 含个人隐私属性的工具（身份证归属地 / 银行卡归属地）仅基于【公开的行政区划代码 / 卡BIN号段】做静态映射演示，
 *   不联网、不采集、不返回任何真实个人隐私数据。
 */
(function () {
  'use strict';

  /* ===================== 公共工具 ===================== */
  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function val(s) { var e = $(s); return e ? e.value.trim() : ''; }
  function out(html) { var e = $('#result'); if (e) e.innerHTML = html; }
  function table(pairs, raw) {
    var h = '<table>';
    pairs.forEach(function (p) {
      h += '<tr><th>' + esc(p[0]) + '</th><td>' + (raw && p[2] ? p[1] : esc(p[1])) + '</td></tr>';
    });
    return h + '</table>';
  }
  function tip(t, cls) { return '<div class="alert-tip ' + (cls || '') + '">' + t + '</div>'; }

  /* ===================== 1. IP 查询 ===================== */
  function initIp() {
    function render(d) {
      out(table([
        ['IP地址', d.ip || d.query || '-'],
        ['国家 / 地区', d.country_name || d.country || '-'],
        ['省份', d.region || d.regionName || '-'],
        ['城市', d.city || '-'],
        ['运营商', d.org || d.isp || d.as || '-'],
        ['经纬度', (d.latitude != null && d.longitude != null) ? (d.latitude + ', ' + d.longitude)
          : ((d.lat != null && d.lon != null) ? (d.lat + ', ' + d.lon) : '-')],
        ['时区', d.timezone || '-'],
        ['邮政编码', d.postal || d.zip || '-']
      ]) + tip('数据来源：公开 IP 归属地接口（ip-api / ipapi.co）。结果仅供参考，可能因代理、CDN 存在偏差。'));
    }
    function norm(p) {
      return {
        ip: p.query, country: p.country, region: p.regionName, city: p.city,
        org: p.isp || p.org, latitude: p.lat, longitude: p.lon, timezone: p.timezone, postal: p.zip
      };
    }
    // 依次尝试的接口：ip-api（快，http）与 ipapi.co（https）
    function mkEndpoints(ip) {
      var ipApi = 'http://ip-api.com/json/' + (ip ? encodeURIComponent(ip) : '') + '?lang=zh-CN';
      var ipapiCo = 'https://ipapi.co/' + (ip ? encodeURIComponent(ip) + '/' : '') + 'json/';
      return location.protocol === 'https:'
        ? [[ipapiCo, 'co'], [ipApi, 'api']]
        : [[ipApi, 'api'], [ipapiCo, 'co']];
    }
    function lookup(ip) {
      out(tip('正在查询…'));
      var list = mkEndpoints(ip), i = 0;
      (function next() {
        if (i >= list.length) { out(tip('查询失败：公开接口暂不可用或本机网络受限，请稍后重试。', 'alert-err')); return; }
        var ep = list[i++];
        fetch(ep[0], { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
          if (ep[1] === 'api') {
            if (d && d.status === 'success') { render(norm(d)); return true; }
          } else {
            if (d && !d.error) { render(d); return true; }
          }
          return false;
        }).catch(function () { return false; }).then(function (ok) { if (!ok) next(); });
      })();
    }
    var b = $('#ipBtn');
    if (b) b.addEventListener('click', function () { lookup(val('#ipInput')); });
    lookup(''); // 打开即显示本机 IP
  }

  /* ===================== 2. 身份证归属地 ===================== */
  var SFZ_PROV = {
    '11': '北京市', '12': '天津市', '13': '河北省', '14': '山西省', '15': '内蒙古自治区',
    '21': '辽宁省', '22': '吉林省', '23': '黑龙江省',
    '31': '上海市', '32': '江苏省', '33': '浙江省', '34': '安徽省', '35': '福建省', '36': '江西省', '37': '山东省',
    '41': '河南省', '42': '湖北省', '43': '湖南省', '44': '广东省', '45': '广西壮族自治区', '46': '海南省',
    '50': '重庆市', '51': '四川省', '52': '贵州省', '53': '云南省', '54': '西藏自治区',
    '61': '陕西省', '62': '甘肃省', '63': '青海省', '64': '宁夏回族自治区', '65': '新疆维吾尔自治区',
    '71': '台湾省', '81': '香港特别行政区', '82': '澳门特别行政区'
  };
  var SFZ_CITY = {
    '110101': '北京市东城区', '110105': '北京市朝阳区', '110108': '北京市海淀区',
    '310101': '上海市黄浦区', '310104': '上海市徐汇区', '310115': '上海市浦东新区',
    '440103': '广东省广州市荔湾区', '440304': '广东省深圳市福田区', '440305': '广东省深圳市南山区',
    '330106': '浙江省杭州市西湖区', '320106': '江苏省南京市鼓楼区', '510107': '四川省成都市武侯区',
    '420106': '湖北省武汉市武昌区', '610113': '陕西省西安市雁塔区', '370102': '山东省济南市历下区',
    '500103': '重庆市渝中区', '230103': '黑龙江省哈尔滨市南岗区', '210102': '辽宁省沈阳市和平区',
    '350203': '福建省厦门市思明区', '430102': '湖南省长沙市芙蓉区', '340104': '安徽省合肥市蜀山区'
  };
  function initSfz() {
    function calc(id) {
      var w = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
      var c = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
      var s = 0;
      for (var i = 0; i < 17; i++) s += parseInt(id.charAt(i), 10) * w[i];
      return c[s % 11];
    }
    var b = $('#sfzBtn');
    if (b) b.addEventListener('click', function () {
      var id = val('#sfzInput').toUpperCase().replace(/\s/g, '');
      if (!id) { out(tip('请输入身份证号码', 'alert-err')); return; }
      if (!/^\d{17}[\dX]$/.test(id)) { out(tip('格式错误：身份证号应为 18 位（最后一位可为 X）。', 'alert-err')); return; }
      var prov = SFZ_PROV[id.substr(0, 2)] || '未知';
      var city = SFZ_CITY[id.substr(0, 6)] || (SFZ_PROV[id.substr(0, 2)] ? '（示例库未收录该区县，仅精确到省）' : '未知');
      var birth = id.substr(6, 4) + '-' + id.substr(10, 2) + '-' + id.substr(12, 2);
      var sex = parseInt(id.charAt(16), 10) % 2 === 1 ? '男' : '女';
      var ok = calc(id) === id.charAt(17);
      out(table([
        ['身份证号', id],
        ['归属省份', prov],
        ['归属地区', city],
        ['出生日期', birth],
        ['性别', sex],
        ['校验位', id.charAt(17) + '（' + (ok ? '校验通过' : '校验不通过') + '）']
      ]) + tip('温馨提示：本结果依据公开的《行政区划代码》静态映射得出，仅供学习参考；请勿用于任何侵犯他人隐私的行为。'));
    });
  }

  /* ===================== 3. 银行卡归属地 ===================== */
  var BANK_BIN = {
    '622202': '中国工商银行 · 借记卡', '622200': '中国工商银行 · 借记卡', '621226': '中国工商银行 · 借记卡',
    '622848': '中国农业银行 · 借记卡', '621661': '中国农业银行 · 借记卡', '622840': '中国农业银行 · 借记卡',
    '621700': '中国建设银行 · 借记卡', '622700': '中国建设银行 · 借记卡', '622280': '中国建设银行 · 借记卡',
    '601382': '中国银行 · 借记卡', '621785': '中国银行 · 借记卡', '621666': '中国银行 · 借记卡',
    '622588': '招商银行 · 借记卡', '622575': '招商银行 · 信用卡', '622260': '交通银行 · 借记卡',
    '622150': '中国邮政储蓄银行 · 借记卡', '621599': '中国邮政储蓄银行 · 借记卡',
    '622155': '兴业银行 · 借记卡', '622908': '兴业银行 · 借记卡', '622689': '中信银行 · 借记卡',
    '622600': '中国民生银行 · 借记卡', '622622': '中国光大银行 · 借记卡', '622521': '浦发银行 · 借记卡'
  };
  function initBank() {
    var b = $('#bankBtn');
    if (b) b.addEventListener('click', function () {
      var no = val('#bankInput').replace(/\s/g, '');
      if (!no || !/^\d{12,19}$/.test(no)) { out(tip('请输入 12~19 位银行卡号。', 'alert-err')); return; }
      var bin6 = no.substr(0, 6), bin8 = no.substr(0, 8);
      var hit = BANK_BIN[bin8] || BANK_BIN[bin6];
      out(table([
        ['银行卡号', no.replace(/\d{4}/g, function (m) { return m + ' '; }).trim()],
        ['卡号长度', no.length + ' 位'],
        ['卡BIN', bin6],
        ['发卡银行 / 卡种', hit || '未收录（示例库仅含常见号段）'],
        ['归属地', hit ? '按发卡行总行库返回（示例）' : '-']
      ]) + tip('免责声明：卡BIN号段为公开信息，本工具仅演示"前6位→发卡行"的映射；<b>本 Demo 不联网、不查询任何真实卡片信息</b>，也不提供余额、户名等隐私数据。'));
    });
  }

  /* ===================== 4. QQ 价格评估 ===================== */
  function initQq() {
    var b = $('#qqBtn');
    if (b) b.addEventListener('click', function () {
      var q = val('#qqInput').replace(/\D/g, '');
      if (!q) { out(tip('请输入 QQ 号码。', 'alert-err')); return; }
      var len = q.length, score = 0, notes = [];
      if (len <= 5) { score += 45; notes.push('稀有短号（' + len + '位）'); }
      else if (len === 6) { score += 38; notes.push('6位靓号'); }
      else if (len === 7) { score += 28; notes.push('7位号'); }
      else if (len === 8) { score += 18; notes.push('8位号'); }
      else if (len === 9) { score += 10; notes.push('9位号'); }
      else { score += 4; notes.push(len + '位长号'); }
      if (/(\d)\1{3,}/.test(q)) { score += 20; notes.push('含四位以上连号（豹子号）'); }
      else if (/(\d)\1{2}/.test(q)) { score += 10; notes.push('含三位连号'); }
      if (/(\d\d)\1{2,}/.test(q)) { score += 15; notes.push('ABAB 重复规律'); }
      if (/0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210/.test(q)) { score += 18; notes.push('含顺子规律'); }
      if (/520|1314|8888|6666|9999|168|518/.test(q)) { score += 8; notes.push('含吉祥数字'); }
      if (/^\d*(\d)\1*$/.test(q)) { score += 12; notes.push('单一数字重复'); }
      score = Math.min(99, score);
      var price;
      if (score >= 80) price = '¥ 8,000 - 50,000+';
      else if (score >= 65) price = '¥ 1,500 - 8,000';
      else if (score >= 50) price = '¥ 500 - 1,500';
      else if (score >= 35) price = '¥ 100 - 500';
      else if (score >= 20) price = '¥ 30 - 100';
      else price = '¥ 10 - 30';
      out('<div style="text-align:center;padding:10px 0 20px"><div class="big-num">' + score + '<small> 分</small></div>' +
        '<div style="color:#888;margin-top:6px">参考估价：<b style="color:#ff7c39;font-size:1.2rem">' + price + '</b></div></div>' +
        table([
          ['QQ号码', q], ['号码位数', len + ' 位'], ['综合评分', score + ' / 100'],
          ['评估要点', notes.join('；')], ['参考估价', price]
        ]) + tip('说明：评估依据号码位数、连号、顺子、ABAB、吉祥数字等常见"靓号"维度自动打分，结果仅供娱乐参考。'));
    });
  }

  /* ===================== 5. 备案查询 ===================== */
  function initBeian() {
    var b = $('#beianBtn');
    if (b) b.addEventListener('click', function () {
      var d = val('#beianInput').replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      if (!d) { out(tip('请输入要查询的域名。', 'alert-err')); return; }
      out(table([
        ['查询域名', d],
        ['查询方式', '跳转工信部官方系统'],
        ['官方入口', '<a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">beian.miit.gov.cn</a>']
      ], true) + tip('备案数据由国家工信部统一管理，本站作为仿站 Demo 不存储备案库，请点击官方入口查询“' + esc(d) + '”的真实备案信息。') +
        '<p style="margin-top:14px"><a class="btn-query" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">前往工信部备案系统 →</a></p>');
    });
  }

  /* ===================== 6. 网名查询 / 生成 ===================== */
  function initWangming() {
    var A = ['温柔的', '可爱的', '高冷的', '佛系的', '努力的', '安静的', '奔跑的', '会飞的', '迷糊的', '追光的', '向阳的', '爱笑的', '贪吃的', '睡不醒的', '慢半拍的'];
    var B = ['小熊', '猫咪', '团子', '汽水', '柚子', '月亮', '星星', '夏天', '晚风', '奶糖', '布丁', '云朵', '荔枝', '橙子', '蘑菇', '汤圆', '梨子', '海盐'];
    var C = ['呀', '儿', '酱', '君', '同学', '小可爱', '不emo', '要开心', '在努力', '呀哈', '很nice'];
    function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
    function gen(n) { var r = []; for (var i = 0; i < n; i++) r.push(pick(A) + pick(B) + pick(C)); return r; }
    function render(list) {
      var h = '';
      list.forEach(function (x) { h += '<span class="tag">' + esc(x) + '</span>'; });
      out('<p style="color:#888;margin:0 0 10px">为你生成 ' + list.length + ' 个网名（点击可复制）：</p>' + h);
      Array.prototype.forEach.call(document.querySelectorAll('.result .tag'), function (t) {
        t.addEventListener('click', function () {
          try {
            navigator.clipboard.writeText(t.textContent);
            var o = t.textContent; t.textContent = '已复制 ✓';
            setTimeout(function () { t.textContent = o; }, 900);
          } catch (e) {}
        });
      });
    }
    function run() {
      var k = val('#wmInput');
      if (k) {
        var list = [];
        ['小', '', '萌', 'の'].forEach(function (p) { list.push(p + k); });
        ['', '酱', '控', '同学', '很酷'].forEach(function (s) { list.push(k + s); });
        render(list.concat(gen(6)));
      } else { render(gen(24)); }
    }
    var b = $('#wmBtn'); if (b) b.addEventListener('click', run);
    run();
  }

  /* ===================== 7. 安全期计算 ===================== */
  function fmt(d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function addD(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
  function initAnquanqi() {
    var b = $('#aqBtn');
    if (b) b.addEventListener('click', function () {
      var s = val('#aqLast'), cyc = parseInt(val('#aqCycle') || '28', 10), men = parseInt(val('#aqMen') || '5', 10);
      if (!s) { out(tip('请选择上次月经开始的日期。', 'alert-err')); return; }
      if (!(cyc >= 20 && cyc <= 45)) { out(tip('月经周期一般填 20~45 天。', 'alert-err')); return; }
      var last = new Date(s.replace(/-/g, '/'));
      if (isNaN(last.getTime())) { out(tip('日期格式错误。', 'alert-err')); return; }
      var next = addD(last, cyc);
      var ovu = addD(next, -14);
      var ovuS = addD(ovu, -5), ovuE = addD(ovu, 4);
      out(table([
        ['上次月经', fmt(last) + ' ~ ' + fmt(addD(last, men - 1))],
        ['月经周期', cyc + ' 天'],
        ['下次月经', fmt(next)],
        ['预计排卵日', fmt(ovu)],
        ['排卵期（易孕）', fmt(ovuS) + ' ~ ' + fmt(ovuE)],
        ['安全期', fmt(addD(last, men)) + ' ~ ' + fmt(addD(ovuS, -1)) + '，及 ' + fmt(addD(ovuE, 1)) + ' ~ ' + fmt(addD(next, -1))]
      ]) + tip('安全期避孕法误差较大（受情绪、作息、疾病影响），<b>不能作为可靠的避孕依据</b>，请遵医嘱选择合适方式。'));
    });
    var d = $('#aqLast'); if (d) d.value = fmt(new Date());
  }

  /* ===================== 8. 邮编查询 ===================== */
  var YOUBIAN = {
    '北京': '100000', '上海': '200000', '天津': '300000', '重庆': '400000',
    '广州': '510000', '深圳': '518000', '杭州': '310000', '南京': '210000', '武汉': '430000', '成都': '610000',
    '西安': '710000', '苏州': '215000', '青岛': '266000', '济南': '250000', '郑州': '450000', '长沙': '410000',
    '合肥': '230000', '福州': '350000', '厦门': '361000', '南昌': '330000', '沈阳': '110000', '大连': '116000',
    '哈尔滨': '150000', '长春': '130000', '石家庄': '050000', '太原': '030000', '呼和浩特': '010000',
    '南宁': '530000', '海口': '570000', '贵阳': '550000', '昆明': '650000', '兰州': '730000', '西宁': '810000',
    '银川': '750000', '乌鲁木齐': '830000', '拉萨': '850000', '温州': '325000', '宁波': '315000', '无锡': '214000',
    '佛山': '528000', '东莞': '523000', '珠海': '519000', '中山': '528400', '烟台': '264000', '潍坊': '261000'
  };
  function initYoubian() {
    function run() {
      var k = val('#ybInput');
      if (!k) { out(tip('请输入城市名或邮政编码。')); return; }
      var rows = [];
      if (/^\d{6}$/.test(k)) { for (var c in YOUBIAN) if (YOUBIAN[c] === k) rows.push([c, YOUBIAN[c]]); }
      else { for (var c2 in YOUBIAN) if (c2.indexOf(k) >= 0) rows.push([c2, YOUBIAN[c2]]); }
      if (!rows.length) { out(tip('示例库未收录“' + esc(k) + '”，可试试：北京、上海、广州、深圳、杭州…')); return; }
      var h = '';
      rows.forEach(function (r) { h += '<span class="tag">' + r[0] + '：' + r[1] + '</span>'; });
      out('<p style="color:#888;margin:0 0 10px">共找到 ' + rows.length + ' 条：</p>' + h);
    }
    var b = $('#ybBtn'); if (b) b.addEventListener('click', run);
  }

  /* ===================== 9. 区号查询 ===================== */
  var QUHAO = {
    '010': '北京市', '021': '上海市', '022': '天津市', '023': '重庆市',
    '020': '广州市', '0755': '深圳市', '0756': '珠海市', '0757': '佛山市', '0769': '东莞市', '0760': '中山市',
    '0571': '杭州市', '0574': '宁波市', '0577': '温州市', '025': '南京市', '0512': '苏州市', '0510': '无锡市',
    '027': '武汉市', '028': '成都市', '029': '西安市', '0531': '济南市', '0532': '青岛市', '0536': '潍坊市',
    '0371': '郑州市', '0731': '长沙市', '0551': '合肥市', '0591': '福州市', '0592': '厦门市', '0791': '南昌市',
    '024': '沈阳市', '0411': '大连市', '0451': '哈尔滨市', '0431': '长春市', '0311': '石家庄市', '0351': '太原市',
    '0471': '呼和浩特市', '0771': '南宁市', '0898': '海口市/三亚市', '0851': '贵阳市', '0871': '昆明市',
    '0931': '兰州市', '0971': '西宁市', '0951': '银川市', '0991': '乌鲁木齐市', '0891': '拉萨市'
  };
  function initQuhao() {
    function run() {
      var k = val('#qhInput');
      if (!k) { out(tip('请输入城市名或区号（如 杭州 或 0571）。')); return; }
      var rows = [];
      if (/^\d{3,4}$/.test(k)) {
        k = k.replace(/^0?/, '0');
        for (var c in QUHAO) if (c === k) rows.push([QUHAO[c], c]);
      } else { for (var c2 in QUHAO) if (QUHAO[c2].indexOf(k) >= 0) rows.push([QUHAO[c2], c2]); }
      if (!rows.length) { out(tip('示例库未收录“' + esc(k) + '”，可试试：北京、上海、杭州、深圳…')); return; }
      var h = '';
      rows.forEach(function (r) { h += '<span class="tag">' + r[0] + '：' + r[1] + '</span>'; });
      out('<p style="color:#888;margin:0 0 10px">共找到 ' + rows.length + ' 条：</p>' + h);
    }
    var b = $('#qhBtn'); if (b) b.addEventListener('click', run);
  }

  /* ===================== 路由 ===================== */
  var MAP = {
    ip: initIp, sfz: initSfz, bank: initBank, qq: initQq, beian: initBeian,
    wangming: initWangming, anquanqi: initAnquanqi, youbian: initYoubian, quhao: initQuhao
  };
  function boot() {
    var t = document.body.getAttribute('data-tool');
    if (t && MAP[t]) { try { MAP[t](); } catch (e) { console.error(e); } }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
