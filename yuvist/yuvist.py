#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""\
Kivy YUV Image Viewer
Copyright (C) 2012 Luuvish <luuvish@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


__version__ = '0.9.2'


import kivy
kivy.require('1.5.1')

from os.path import basename, join

from kivy.app import App
from kivy.properties import BooleanProperty, StringProperty, ListProperty, ObjectProperty
from kivy.uix.gridlayout import GridLayout

from uix.dialog_open import OpenDialog
from uix.dialog_yuv_cfg import YuvCfgDialog
from uix.dialog_playlist import PlaylistDialog


class Yuvist(GridLayout):

    popup            = ObjectProperty(None, allownone=True)
    front            = ObjectProperty(None)
    display          = ObjectProperty(None)
    desktop_size     = ListProperty([0, 0])
    fullscreen       = BooleanProperty(False)
    allow_fullscreen = BooleanProperty(True)

    playpath         = StringProperty('.')
    playlist         = ListProperty([])

    def __init__(self, **kwargs):

        super(Yuvist, self).__init__(**kwargs)

        from kivy.core.window import Window
        self.desktop_size = kwargs.get('desktop_size', Window.size)

        Window.bind(on_dropfile=self._drop_file)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, Window)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        self.front.bind(on_load_video=self._on_load_video,
                        on_prev_video=self._on_prev_video,
                        on_next_video=self._on_next_video,
                        on_open_file=self._on_open_file,
                        on_config_yuv_cfg=self._on_config_yuv_cfg,
                        on_config_playlist=self._on_config_playlist)

    def on_fullscreen(self, instance, value):
        window = self.get_parent_window()
        if not window:
            Logger.warning('VideoPlayer: Cannot switch to fullscreen, window not found.')
            if value:
                self.fullscreen = False
            return
        if not self.parent:
            Logger.warning('VideoPlayer: Cannot switch to fullscreen, no parent.')
            if value:
                self.fullscreen = False
            return

        if value:
            self._fullscreen_state = state = {
                'parent':          self.parent,
                'pos':             self.pos,
                'size':            self.size,
                'pos_hint':        self.pos_hint,
                'size_hint':       self.size_hint,
                'window_children': window.children[:]
            }

            # remove all window children
            for child in window.children[:]:
                window.remove_widget(child)

            # put the video in fullscreen
            if state['parent'] is not window:
                state['parent'].remove_widget(self)
            window.add_widget(self)

            # ensure the video widget is in 0, 0, and the size will be reajusted
            self.pos = (0, 0)
            self.size = (100, 100)
            self.pos_hint = {}
            self.size_hint = (1, 1)

            self.prev_size = window.size
            window.size = self.desktop_size
        else:
            state = self._fullscreen_state
            window.remove_widget(self)
            for child in state['window_children']:
                window.add_widget(child)
            self.pos_hint = state['pos_hint']
            self.size_hint = state['size_hint']
            self.pos = state['pos']
            self.size = state['size']
            if state['parent'] is not window:
                state['parent'].add_widget(self)

            window.size = self.prev_size

        window.fullscreen = value

    def _on_load_video(self, front, value):

        self.display.clear_widgets()
        self.display.add_widget(front._video)

        source, format, colorfmt, yuv_size, yuv_fps = value

        window = self.get_parent_window()
        if window:
            window.title = '%s %s:%s@%2.f' % (
                basename(source),
                '%dx%d' % tuple(yuv_size),
                format.upper(),
                yuv_fps
            )

        playlist = self.playlist[:]
        for playitem in playlist:
            if playitem[0] == source:
                playitem[1:] = value[1:]
                return
        self.playlist.append(value[:])

    def _on_prev_video(self, front, *largs):
        playitem = front.playitem
        playlist = self.playlist[:]
        for i in xrange(len(playlist)):
            if playlist[i][0] == playitem[0] and i > 0:
                front.playitem = playlist[i-1][:]
                front.state = 'play'
                return

    def _on_next_video(self, front, *largs):
        playitem = front.playitem
        playlist = self.playlist[:]
        for i in xrange(len(playlist)):
            if playlist[i][0] == playitem[0] and i < len(playlist)-1:
                front.playitem = playlist[i+1][:]
                front.state = 'play'
                return

    def _on_open_file(self, front, *largs):
        def confirm(path, filename):
            self.playpath = path
            front.source = join(path, filename)
            front.state = 'play'
        window = self.get_parent_window()
        size = (window.size[0] - 160, window.size[1] - 100) if window else (700, 500)
        popup = OpenDialog(path=self.playpath, confirm=confirm, size=size)
        popup.open()

    def _on_config_yuv_cfg(self, front, *largs):
        def confirm(format, yuv_size):
            front.playitem = [front.source, format, front.colorfmt, yuv_size, front.yuv_fps]
            front.state = 'play'
        popup = YuvCfgDialog(format=front.format, yuv_size=front.yuv_size, confirm=confirm)
        popup.open()

    def _on_config_playlist(self, front, *largs):
        def confirm(playitem):
            front.playitem = playitem[:]
            front.state = 'play'
        window = self.get_parent_window()
        size = (window.size[0] - 160, window.size[1] - 100) if window else (700, 500)
        popup = PlaylistDialog(playlist=self.playlist, confirm=confirm, size=size)
        popup.open()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        from kivy.utils import platform

        if keycode[1] == '0' and 'meta' in modifiers:
            return self._resize(size_hint=(0.5, 0.5))
        if keycode[1] == '1' and 'meta' in modifiers:
            return self._resize(size_hint=(1.0, 1.0))
        if keycode[1] == '2' and 'meta' in modifiers:
            return self._resize(size_hint=(2.0, 2.0))
        if keycode[1] == '3' and 'meta' in modifiers:
            return self._resize(size_hint=(0.5, 0.5))
        if keycode[1] == 'F' and 'meta' in modifiers:
            return self._resize(size_hint=(0.5, 0.5))

        if keycode[1] == 'enter':
            if self.allow_fullscreen:
                self.fullscreen = not self.fullscreen
            return True

        if keycode[1] == 'up':
            volume = self.front.volume
            volume += 0.1
            if volume > 1.0:
                volume = 1.0
            self.front.volume = volume
            return True
        if keycode[1] == 'down':
            volume = self.front.volume
            volume -= 0.1
            if volume < 0.0:
                volume = 0.0
            self.front.volume = volume
            return True
        if keycode[1] == 'down' and 'meta' in modifiers and 'alt' in modifiers:
            self.front.volume = 0.0
            return True

        if keycode[1] == 'home':
            self.front.seek(0.)
            return True
        if keycode[1] == 'end':
            self.front.seek(1.)
            return True

        if keycode[1] == 'left' and 'meta' in modifiers and 'alt' in modifiers:
            self.front.dispatch('on_prev_video')
            return True
        if keycode[1] == 'right' and 'meta' in modifiers and 'alt' in modifiers:
            self.front.dispatch('on_next_video')
            return True
        if keycode[1] == '[':
            self.front.dispatch('on_prev_frame')
            return True
        if keycode[1] == ']':
            self.front.dispatch('on_next_frame')
            return True
        if keycode[1] == 'spacebar':
            self.front.dispatch('on_play_pause')
            return True

        if keycode[1] == 'o' and 'meta' in modifiers:
            self.front.dispatch('on_open_file')
            return True
        if keycode[1] == 'c' and 'meta' in modifiers and 'alt' in modifiers:
            self.front.dispatch('on_config_yuv_cfg')
            return True
        if keycode[1] == 'l' and 'meta' in modifiers and 'alt' in modifiers:
            self.front.dispatch('on_config_playlist')
            return True

        return True

    def _resize(self, size_hint=(1., 1.)):
        window = self.get_root_window()
        size   = self.video.resolution
        ratio  = size[0] / float(size[1])
        w, h   = 1920, 1080 #window._size
        tw, th = int(size[0] * size_hint[0]), int(size[1] * size_hint[1]) + 62
        iw = min(w, tw)
        ih = iw / ratio
        if ih > h:
            ih = min(h, th)
            iw = ih * ratio
        window.size = int(iw), int(ih)
        return True

    def _drop_file(filename):
        print 'dropfile %s' % filename
        self.source = filename
        self.state = 'play'


class YuvistApp(App):

    title = 'Yuvist-' + __version__
    icon  = 'data/images/yuvist.png'

    def __init__(self, **kwargs):

        super(YuvistApp, self).__init__(**kwargs)

        import pygame
        pygame.display.init()
        info = pygame.display.Info()
        self.desktop_size = [info.current_w, info.current_h]

        self.filename = kwargs.get('filename', '')
        self.format   = kwargs.get('format', 'yuv420')
        self.yuv_size = kwargs.get('yuv_size', [1920, 1080])
        self.state    = kwargs.get('state', 'pause')

    def build(self):
        return Yuvist(source=self.filename,
                      format=self.format,
                      yuv_size=self.yuv_size,
                      state=self.state,
                      desktop_size=self.desktop_size)


if __name__ == '__main__':

    print("Kivy YUV Image Viewer")
    print("Copyright (C) 2012 Luuvish <luuvish@gmail.com>")

    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else ''
    app = YuvistApp(filename=filename)
    app.run()
