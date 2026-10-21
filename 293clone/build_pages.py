# -*- coding: utf-8 -*-
"""293查询 仿站 · 工具页生成器：由模板批量生成 9 个查询子页。"""
import os

TPL = """<!DOCTYPE HTML>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="applicable-device" content="pc,mobile">
<meta name="description" content="{desc}">
<meta name="keywords" content="293查询,{title}">
<title>{title} - 293查询</title>
<link href="style/bootstrap.min.css" rel="stylesheet" type="text/css"/>
<link href="style/new.css" rel="stylesheet" type="text/css"/>
<link href="style/site.css" rel="stylesheet" type="text/css"/>
</head>
<body data-tool="{tool}">

<div id="site-nav"></div>

<div class="container">
<section>
  <div class="tool-head">
    <img src="images/{img}" alt="{title}">
    <div>
      <h2>{title}</h2>
      <p>{desc}</p>
    </div>
  </div>

  <div class="tool-card">
    <form onsubmit="return false;">
{form}
    </form>
    <div class="result" id="result"></div>
  </div>
</section>
</div>

<div id="site-footer"></div>

<script src="js/jquery-3.3.1.min.js"></script>
<script src="js/bootstrap.min.js"></script>
<script src="js/layout.js"></script>
<script src="js/tools.js"></script>
</body>
</html>
"""

TOOLS = [
    dict(tool="ip", img="ip.png", title="IP查询", file="ip.html",
         desc="查询本机IP或指定IP地址的归属地、运营商与地理位置信息。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="ipInput" class="form-control" placeholder="留空则查询本机IP，或输入 IPv4 / IPv6 地址">
        </div>
        <div class="col-md-4">
          <button type="button" id="ipBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
    dict(tool="sfz", img="sfz.png", title="身份证查询", file="sfz.html",
         desc="通过身份证号码前6位查询户籍所在地区，并校验证件号码格式。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="sfzInput" class="form-control" maxlength="18" placeholder="请输入 18 位身份证号码，例如 11010119900307xxxx">
        </div>
        <div class="col-md-4">
          <button type="button" id="sfzBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
    dict(tool="bank", img="bank.png", title="银行卡归属地查询", file="bank.html",
         desc="通过银行卡号查询该卡的相关信息，包括卡名称、银行卡卡种、卡品牌、银行卡发卡行、以及归属地等信息。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="bankInput" class="form-control" placeholder="请输入 12~19 位银行卡号">
        </div>
        <div class="col-md-4">
          <button type="button" id="bankBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
    dict(tool="qq", img="qq.png", title="QQ价格评估", file="qq.html",
         desc="一键评估 QQ 号码价值，综合号码位数、靓号规律等维度给出参考估价。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="qqInput" class="form-control" placeholder="请输入 QQ 号码，例如 10001">
        </div>
        <div class="col-md-4">
          <button type="button" id="qqBtn" class="btn-query">立即评估</button>
        </div>
      </div>"""),
    dict(tool="beian", img="beian.png", title="备案查询", file="beian.html",
         desc="查看域名是否已经备案及备案情况。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="beianInput" class="form-control" placeholder="请输入域名，例如 beian.miit.gov.cn">
        </div>
        <div class="col-md-4">
          <button type="button" id="beianBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
    dict(tool="wangming", img="wangming.png", title="网名查询", file="wangming.html",
         desc="微信QQ个性昵称，男生、女生、情侣微信QQ网名查询与生成。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="wmInput" class="form-control" placeholder="可选：输入关键词（留空则随机生成 24 个网名）">
        </div>
        <div class="col-md-4">
          <button type="button" id="wmBtn" class="btn-query">换一批</button>
        </div>
      </div>"""),
    dict(tool="anquanqi", img="anquanqi.png", title="安全期查询", file="anquanqi.html",
         desc="输入上次月经时间与周期，自动计算安全期、排卵期与下次月经日期。",
         form="""      <div class="form-row">
        <div class="col-md-4 mb-2">
          <label>上次月经开始日期</label>
          <input type="date" id="aqLast" class="form-control">
        </div>
        <div class="col-md-3 mb-2">
          <label>月经周期（天）</label>
          <input type="number" id="aqCycle" class="form-control" value="28" min="20" max="45">
        </div>
        <div class="col-md-3 mb-2">
          <label>经期天数</label>
          <input type="number" id="aqMen" class="form-control" value="5" min="2" max="10">
        </div>
        <div class="col-md-2 mb-2" style="display:flex;align-items:flex-end">
          <button type="button" id="aqBtn" class="btn-query" style="width:100%">计算</button>
        </div>
      </div>"""),
    dict(tool="youbian", img="youbian.png", title="邮编查询", file="youbian.html",
         desc="按省市或地区名快速查询邮政编码。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="ybInput" class="form-control" placeholder="请输入城市名或 6 位邮编，例如 杭州 或 310000">
        </div>
        <div class="col-md-4">
          <button type="button" id="ybBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
    dict(tool="quhao", img="quhao.png", title="区号查询", file="quhao.html",
         desc="查询全国各省市固定电话区号，支持城市名与区号双向查询。",
         form="""      <div class="form-row">
        <div class="col-md-8 mb-2">
          <input type="text" id="qhInput" class="form-control" placeholder="请输入城市名或区号，例如 杭州 或 0571">
        </div>
        <div class="col-md-4">
          <button type="button" id="qhBtn" class="btn-query">立即查询</button>
        </div>
      </div>"""),
]

outdir = os.path.dirname(os.path.abspath(__file__))
for t in TOOLS:
    html = TPL.format(**t)
    with open(os.path.join(outdir, t["file"]), "w", encoding="utf-8") as f:
        f.write(html)
    print("生成:", t["file"])
print("完成，共 %d 个工具页" % len(TOOLS))
