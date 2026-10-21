/* 293查询 仿站 · 公共导航与页脚 */
(function () {
  'use strict';

  var NAV = '' +
    '<nav class="navbar navbar-expand-sm navbar-dark" style="background:#3b5999">' +
      '<a class="navbar-brand" href="index.html">首页</a>' +
      '<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#collapsibleNavbar">' +
        '<span class="navbar-toggler-icon"></span>' +
      '</button>' +
      '<div class="collapse navbar-collapse" id="collapsibleNavbar">' +
        '<ul class="navbar-nav mr-auto">' +
          '<li class="nav-item"><a class="nav-link" href="ip.html">IP查询</a></li>' +
          '<li class="nav-item"><a class="nav-link" href="sfz.html">身份证查询</a></li>' +
          '<li class="nav-item"><a class="nav-link" href="bank.html">银行卡归属地查询</a></li>' +
          '<li class="nav-item"><a class="nav-link" href="qq.html">qq价格评估</a></li>' +
          '<li class="nav-item"><a class="nav-link" href="beian.html">备案查询</a></li>' +
          '<li class="nav-item"><a class="nav-link" href="wangming.html">网名查询</a></li>' +
        '</ul>' +
        '<nav class="my-2 my-md-0 float-right">' +
          '<img src="images/logo.svg" onclick="location.href=\'index.html\'" alt="293查询网" style="width:130px;height:40px;cursor:pointer;">' +
        '</nav>' +
      '</div>' +
    '</nav>';

  var FOOTER = '' +
    '<footer class="site-footer">' +
      '<div class="container">' +
        '<p>293查询 · 综合信息查询大全（前端仿站练习版）</p>' +
        '<p>IP查询 · 身份证归属地 · 银行卡归属地 · 备案查询 · 网名查询 · 邮编区号 · 安全期计算</p>' +
        '<p class="small">本站为前端仿站 Demo，仅供学习交流，不提供任何真实个人隐私数据的查询服务。</p>' +
      '</div>' +
    '</footer>';

  function mount() {
    var n = document.getElementById('site-nav');
    if (n) n.innerHTML = NAV;
    var f = document.getElementById('site-footer');
    if (f) f.innerHTML = FOOTER;
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
