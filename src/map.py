""" Módulo responsável pelas mecânicas do mapa do jogo """


import pygame
from map_node import MapNode, MapNodeType, Point
import math
import random
from screen import Screen


SCROLL_SPEED = 7
MARGIN = 20


class MapScreen(Screen):
    def __init__(self, target: pygame.Surface, root: MapNode):
        self._load_sprites()
        self.pos = pygame.math.Vector2(target.get_size())
        self.pos -= self.map_sprite.get_size()
        self.pos /= 2

        self.target = target
        
        self.root = root
        self.nodes = set([root])
        self._add_children(root)

        self.hovered_node = None
        self.current_node = root
        self.choosen_node = None
        root.activate()

        self.scrolling = False
        self.scroll_initial_y = 0

        self.scroll_interval = (self.pos.y * 2 - MARGIN, MARGIN)
        self._scroll_to(root)

        for node in self.nodes:
            self._bake_trail(node)

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEMOTION:
            self._mouse_motion(ev.dict["pos"])

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_down(ev.dict["pos"], ev.dict["button"])

        elif ev.type == pygame.MOUSEBUTTONUP:
            self._mouse_up(ev.dict["pos"], ev.dict["button"])

        elif ev.type == pygame.MOUSEWHEEL:
            self.hovered_node = None
            self.pos.y = pygame.math.clamp(
                self.pos.y + ev.dict["y"] * SCROLL_SPEED,
                self.scroll_interval[0],
                self.scroll_interval[1],
            )

    def update(self):
        if self.choosen_node != None:
            return self.choosen_node.screen

    def draw(self):
        self.target.fill((0,0,0))
        self.target.blit(self.map_sprite, self.pos)

        for node in self.nodes:
            self._render_node(node)

    # Torna o nó atual visível na região inferior da tela, alterando a posição
    # Y em que o mapa é desenhado
    def _scroll_to(self, node: MapNode):
        self.pos.y = pygame.math.clamp(
            (self.target.get_height() * 3/4) - node.pos.y,
            self.scroll_interval[0],
            self.scroll_interval[1],
        )

    def _mouse_motion(self, mouse_pos: Point):
        if self.scrolling:
            self.pos.y = pygame.math.clamp(
                mouse_pos[1] - self.scroll_initial_y,
                self.scroll_interval[0],
                self.scroll_interval[1],
            )

        for node in self.nodes:
            if not node.is_navigable: continue
            
            dist = (node.pos - mouse_pos + self.pos).length()

            if (dist < self._node_radius(node)):
                self.hovered_node = node
                return

        self.hovered_node = None

    def _mouse_down(self, mouse_pos: Point, button: int):
        if button != 1: return
        
        if self.hovered_node != None:
            self.current_node.navigate_to(self.hovered_node)
            self._bake_trail(self.hovered_node)
            self._bake_trail(self.current_node)

            self.current_node = self.hovered_node
            self.choosen_node = self.hovered_node
            self.hovered_node = None
        else:
            self.scrolling = True
            self.scroll_initial_y = mouse_pos[1] - self.pos.y

    def _mouse_up(self, mouse_pos: Point, button: int):
        if button == 1:
            self.scrolling = False

    def _load_sprites(self):
        self.map_sprite = pygame.image.load("assests/map_bg.png").convert_alpha()

        ss = pygame.image.load("assests/map_icons.png").convert_alpha()
        self.node_sprites = [
            ss.subsurface((142, 0,  48, 48)), # nó de batalha inacessível
            ss.subsurface((142, 48, 48, 48)), # nó de história inacessível
            ss.subsurface((128, 96, 64, 64)), # nó de boss inacessível
            ss.subsurface((96,  0,  48, 48)), # nó ... já visitado
            ss.subsurface((96,  48, 48, 48)),
            ss.subsurface((0,   96, 64, 64)),
            ss.subsurface((0,   0,  48, 48)), # nó ... acessível
            ss.subsurface((0,   48, 48, 48)),
            ss.subsurface((0,   96, 64, 64)),
            ss.subsurface((48,  0,  48, 48)), # nó ... sendo selecionado
            ss.subsurface((48,  48, 48, 48)),
            ss.subsurface((64,  96, 64, 64)),
        ]

        self.trail_marks_sprite = pygame.image.load("assests/map_trail_marks.png").convert_alpha()

    def _add_children(self, node: MapNode):
        self.nodes.update(node.children)
        for child in node.children:
            self._add_children(child)

    # Desenha as arestas entre um nó e todos os seus "filhos". O desenho é feito
    # diretamente na textura do mapa ao invés de na tela, o que permite com que
    def _bake_trail(self, origin: MapNode):
        for child in origin.children:
            diff_raw = child.pos - origin.pos
            diff_normal = diff_raw.normalize()

            start = origin.pos + diff_normal * self._node_radius(origin)
            end = child.pos - diff_normal * self._node_radius(child)

            diff = end - start

            distance = diff.length()
            angle_idx = math.floor(.5 - math.atan2(diff.y, diff.x) * 12 / math.pi)

            num_marks = math.floor(distance / 16)
            inc = diff / num_marks if num_marks != 0 else pygame.math.Vector2(0, 0)

            for i in range(num_marks + 1):
                x = (int(origin.pos.x) + i) % 4
                x += 4 * (child.is_navigable or child.was_visited)
                y = angle_idx % 6

                sprite = self.trail_marks_sprite.subsurface((x << 4, y << 4, 16, 16))

                if (angle_idx % 12) >= 6:
                    sprite = pygame.transform.rotate(sprite, 90)

                p = start + inc * i if num_marks > 0 else (start + end) / 2
                s = pygame.math.Vector2(sprite.get_size())
                self.map_sprite.blit(sprite, p - s / 2)

    # Renderiza um único nó
    def _render_node(self, node: MapNode):
        sprite_id = node.was_visited + \
                    (node.is_navigable << 1) + \
                    (node == self.hovered_node)

        # Decide, pelas propriedades do nó, qual será desenhado na tela.
        # Ver `_load_sprites` para entender a fórmula
        sprite_id = len(MapNodeType) * sprite_id + node.type.value

        sprite = self.node_sprites[sprite_id]
        w, h = sprite.get_size()
        self.target.blit(sprite, node.pos - (w >> 1, h >> 1) + self.pos)

    # O raio de um nó. Usado para detecção do hover do mouse e para saber até
    # onde desenhar os caminhos que incidem no nó em `_bake_trail`
    def _node_radius(self, node: MapNode):
        return 32 if node.type == MapNodeType.BOSS else 20