import unittest
from backend.aihubmix_video import WanAdapter
from backend.video_prompt import compile
class WanDialogueTests(unittest.TestCase):
 def test_configuration(self):
  p=WanAdapter().profile()
  self.assertEqual(p['model'],'wan3.0-video')
 def test_dialogue_replaces_silence(self):
  inputs=dict(shot=dict(prompt='一镜到底，无台词',dialogue='朱云：臣愿直言。'),references=[],people=[],clue={})
  text=compile(inputs,5,'古画风格')
  self.assertIn('朱云：臣愿直言。',text)
  self.assertNotIn('无台词',text)
 def test_empty_dialogue_is_silent(self):
  text=compile(dict(shot=dict(prompt='单镜头'),references=[],people=[],clue={}),5,'古画')
  self.assertIn('无台词',text)

class StoryFirstTests(unittest.TestCase):
 def test_early_petition_does_not_copy_arrest_scene(self):
  inputs=dict(shot=dict(prompt='保持原画人物位置，侍卫抓住双手',action='保持原画姿态',startFrame='依照原画站位',style='保留古画笔触与构图，动作克制'),references=[],people=[],clue=dict(name='朱云当廷直谏 · 1',summary='朱云进言，请求斩佞臣'))
  text=compile(inputs,5,'保留笔触')
  self.assertIn('朱云双手自由',text)
  self.assertIn('均不是首帧或尾帧',text)
  self.assertIn('不得出现侍卫',text)
  self.assertNotIn('侍卫抓住双手',text)
  self.assertNotIn('保持原画姿态',text)
  self.assertNotIn('保留古画笔触与构图',text)
