# -*- coding: utf-8 -*-
"""分段粘贴正文+插入游戏截图到公众号编辑器"""
import sys, io, time, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pyperclip

IMG_DIR = r'D:\7tan\7tanAI\downloads\article4_shots'

# 段落与图片序列：None 表示文本段落，str 表示图片文件名
SEQUENCE = [
    ("text", "大家好，我是7233游戏盒，一个专注挖掘好游戏的搬运工。\n\n最近总有朋友问我：手机里到底装什么游戏才不会吃灰？\n\n说实话，我测试过上百款手游，最后真正留下来、反复打开的就那么几款。它们不一定最火，但一定最上头——有的让我笑到邻居敲门，有的让我在深夜默默流泪，还有的让我和陌生人成了固定队友。\n\n今天全部掏出来，一次性安利给你。\n\n🎮 01 | 蛋仔派对：5亿人挤在同一个岛上\n\n如果说有一款游戏能让你的家族群、同学群、同事群同时活跃起来，那一定是它。\n\n国民级乐园游戏，5亿玩家不是吹的。Q萌的小蛋仔在盲盒世界蹦蹦跳跳，上百张风格各异的地图，从竞速闯关到躲猫猫，手残党也能玩出花来。最绝的是它的创意工坊——上亿张玩家自制的乐园地图，别人挖空心思设计的关卡，你免费就能玩。\n\n下班后和好友开黑互坑，一局就笑到肚子疼。快乐，真的是可以滚起来的。"),
    ("img", "蛋仔派对_1.jpg"),
    ("text", "\n🎮 02 | 光·遇：玩哭了，也治愈了\n\n如果说蛋仔是快乐，那光·遇就是温柔本身。\n\n制作人陈星汉，就是那个做出《风之旅人》的男人。这款游戏他打磨了七年，七年磨一剑，一剑封神。\n\n你化身小小的光之使者，在云端王国翱翔，和来自世界各地、素不相识的人牵手同行。没有文字聊天，没有战力排名，只有光影、音乐和最纯粹的陪伴。当你在暴风雨里筋疲力尽，陌生人点亮蜡烛为你指路的那一刻——真的会鼻子一酸。\n\n有人说这是\"社交游戏的天花板\"，我觉得它更像一个会发光的树洞，安放所有疲惫。"),
    ("img", "光遇_1.jpg"),
    ("text", "\n🎮 03 | 巅峰极速：手机上的3A级赛车\n\n男人至死是少年，看到法拉利就挪不开眼。\n\n网易和英国老牌赛车厂商Codemasters深度合作，100多款正版授权豪车——法拉利、兰博基尼、保时捷、布加迪、帕加尼，全是真车数据一比一还原，连内饰按钮、轮毂螺丝都给你建模出来。\n\n哈尔滨、重庆、上海、纽北、巴塞罗那……全球真实赛道随便飙。引擎的轰鸣声是录制真车声音做的，戴上耳机那一刻，热血直接冲上头顶。手机上能玩到这个画质和手感，真的离谱。"),
    ("img", "巅峰极速_1.jpg"),
    ("text", "\n🎮 04 | 崩坏：星穹铁道：剧情能追番的银河冒险\n\n如果你喜欢剧情像追番一样的游戏，米哈游的这款星穹铁道闭眼入。\n\n坐上星穹列车，穿越银河，造访一个又一个光怪陆离的星球世界。每个星球都是一整部电影的体量，剧情、音乐、演出全部拉满，角色个个有血有肉，连反派都让人心疼。最近还和《Fate》联动，免费送吉尔伽美什和Archer二选一，童年回忆直接杀回来。\n\n战斗是指令式回合制，不考验手速，只考验策略，上班族摸鱼也能轻松玩。680万下载量，口碑豆瓣级稳定。"),
    ("img", "崩坏星穹铁道_1.jpg"),
    ("text", "\n🎮 05 | 鹅鸭杀：一局笑出腹肌的动物狼人杀\n\n压轴必须是它——今年最让人上头的社交推理游戏。\n\n你是一只鹅，队友也是一群鹅，但鹅群里混进了几只鸭子。开会、推理、投票、刀人……规则简单到3分钟上手，但每一局都能玩出无数种骚操作。和朋友开黑，前一秒还在互称好兄弟，后一秒就指着对方鼻子喊\"你就是那只鸭！\"\n\n央视86版《西游记》都来联动了，孙悟空和猪八戒皮肤直接安排。一局20分钟，笑声能持续一整晚。"),
    ("img", "鹅鸭杀_1.jpg"),
    ("text", "\n写在最后\n\n这5款游戏，从爆笑到治愈，从热血到烧脑，刚好覆盖你一天24小时的所有情绪。\n\n你最想先玩哪一款？欢迎在评论区告诉我，呼声最高的我下一篇写详细攻略。\n\n如果这篇对你有用，点个「在看」，让更多朋友告别游戏荒。\n\n关注「7233游戏盒」，每周为你挖掘真正好玩的游戏，我们下期见！"),
]

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.0)
    print('  text pasted, len=', len(text))

def paste_image(filename):
    path = IMG_DIR + '\\' + filename
    # PowerShell 把图片放入剪贴板
    cmd = f"powershell -Command \"Set-Clipboard -Path '{path}'\""
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=30)
    time.sleep(0.8)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    print('  image pasted:', filename)

def main():
    # 点击正文区域（作者框下方，正文开始处）
    pyautogui.click(500, 560)
    time.sleep(0.8)
    pyautogui.click(500, 560)
    time.sleep(0.5)
    print('clicked body area')
    for kind, content in SEQUENCE:
        if kind == 'text':
            paste_text(content)
        else:
            paste_image(content)
    print('ALL DONE')

if __name__ == '__main__':
    main()
