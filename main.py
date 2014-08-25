import sys
import os

import pygame

class Object(pygame.sprite.Sprite):
    def __init__(self, name, image, width, height):
        pygame.sprite.Sprite.__init__(self)

        self.name = name
        self.image = pygame.image.load(os.path.join('assets', image))
        self.width = width
        self.height = height

        self.rect = pygame.Rect(0,0,width,height)

        self.frames = {}
        self.anim = 'idle'
        self.setup_frames('idle', 0, 2)
        self.frame = 0
        self.frametime = 0.0
        self.frametime_max = 10.0

        self.reqs = []
        self.unreqs = []
        self.parents = []
        self.type = ''

        self.message = ""
        self.error = "" # message when reqs aren't met
        self.response = "" # message when toggled

        self.breaks = False

        self.view = None # objects are only visible when on a specific view

    def set_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    # pickup, npc, toggle, door, use
    def set_type(self, typ, extra=None):
        self.type = typ
        if typ == 'pickup':
            self.uses = 1
        if typ == 'door':
            self.to = extra

    def set_view(self, world, loc):
        self.view = (world, loc)

    def setup_frames(self, anim, row, num):
        self.frames[anim] = []
        for i in range(0, num):
            newframe = self.image.subsurface(i*self.width, row*self.height, self.width, self.height)
            self.frames[anim].append(newframe)

    def animate(self, dt):
        # object is animated
        if len(self.frames) != 0:
            self.frametime += dt

            if self.frametime > self.frametime_max:
                self.frame = (self.frame + 1) % len(self.frames[self.anim])
                self.frametime = 0.0

    def draw(self, display, world, loc):
        if self.view == None or (self.view[0] == world and self.view[1] == loc):
            #pygame.draw.rect(display, (200,60,60,20), self.rect)
            display.blit(self.frames[self.anim][self.frame], self.rect)

    def set_anim(self, name):
        #self.frame = 0
        #self.frametime = 0
        self.anim = name

    def add_req(self, name):
        self.reqs.append(name)

    # object must be grabbed to use this object
    def add_unreq(self, name):
        self.unreqs.append(name)

    # object must be toggled on to use this object
    def add_parent(self, name):
        self.parents.append(name)

    def set_messages(self, message=None, error=None, response=None):
        if message:
            self.message = message
        if error:
            self.error = error
        if response:
            self.response = response

    def can_use(self, player, objects, objects2, objects3):
        r = []
        if self.breaks:
            return False

        for req in self.reqs:
            if req not in player.inventory.keys():
                return False
            r.append(req)

        for unreq in self.unreqs:
            for obj in objects:
                if unreq == obj.name:
                    return False

        for parent in self.parents:
            for obj in objects:
                # object is a parent and not toggled on
                if obj.name == parent and obj.anim == 'idle':
                    return False
            for obj in objects2:
                # object is a parent and not toggled on
                if obj.name == parent and obj.anim == 'idle':
                    return False
            for obj in objects3:
                # object is a parent and not toggled on
                if obj.name == parent and obj.anim == 'idle':
                    return False


        for req in r:
            if req != 'balloon' and req != 'milk':
                player.inventory[req]['uses'] -= 1
                if player.inventory[req]['uses'] <= 0:
                    player.inventory.pop(req)

        return True

    def set_uses(self, num):
        self.uses = num

    def set_breaks(self):
        self.breaks = True


class Player(Object):
    def __init__(self, name, image, width, height):
        Object.__init__(self, name, image, width, height)

        self.xspeed = 20.0
        self.yspeed = 10.0

        self.view_border = 50

        self.inventory = {}
        self.swaps = {}

        # interacting starts the timer,
        # when it reaches zero,
        # you can interact again
        self.timer_max = 10.0
        self.timer = self.timer_max

    def move(self, dt, keys, restr):
        if self.timer > 0.0:
            self.timer -= dt
        if (keys[pygame.K_LEFT] or keys[pygame.K_s]):
            if self.rect.centerx > restr['left']:
                self.rect = self.rect.move(-self.xspeed * dt, 0)
                self.set_anim('left')
            else:
                self.rect.centerx = restr['left']
        if (keys[pygame.K_RIGHT] or keys[pygame.K_f]):
            if self.rect.centerx < restr['right']:
                self.rect = self.rect.move(self.xspeed * dt, 0)
                self.set_anim('right')
            else:
                self.rect.centerx = restr['right']
        if (keys[pygame.K_UP] or keys[pygame.K_e]):
            if self.rect.bottom > restr['top']:
                self.rect = self.rect.move(0, -self.yspeed * dt)
                self.set_anim('up')
            else:
                self.rect.bottom = restr['top']
        if (keys[pygame.K_DOWN] or keys[pygame.K_d]):
            if self.rect.bottom < restr['bot']:
                self.rect = self.rect.move(0, self.yspeed * dt)
                self.set_anim('idle')
            else:
                self.rect.bottom = restr['bot']

    def change_view(self, width, world):
        if len(world) != 1:
            if self.rect.centerx < self.view_border:
                self.set_pos(450, self.rect.y)
                return -1
            if self.rect.centerx > width - self.view_border:
                self.set_pos(200, self.rect.y)
                return 1
        return 0

    def start_timer(self):
        self.timer = self.timer_max

    def interact(self, game, objects, objects2, objects3):
        if self.timer <= 0.0:
            for obj in objects:
                if self.rect.colliderect(obj.rect) and (game.world == obj.view[0] and game.loc == obj.view[1]):
                    self.start_timer()
                    # PICKUP
                    if obj.type == 'pickup' or obj.type == 'use':
                        if obj.can_use(self, objects, objects2, objects3): # pickup the object
                            self.check_swaps(obj, game)
                            if obj.type == 'pickup':
                                game.sound_pickup.play()
                                new_item = pygame.image.load(os.path.join('assets', obj.name+'_inv'+'.png'))
                                self.inventory[obj.name] = {'image': new_item, 'uses': obj.uses}
                            else:
                                game.sound_toggle.play()
                            if self.rect.y < 200:
                                game.message(self.rect.x, self.rect.y + self.height/2, obj.message)
                            else:
                                game.message(self.rect.x, self.rect.y - self.height/2, obj.message)
                            objects.remove(obj)
                        else:
                            game.sound_etoggle.play()
                            if self.rect.y < 200:
                                game.message(self.rect.x, self.rect.y + self.height/2, obj.error)
                            else:
                                game.message(self.rect.x, self.rect.y - self.height/2, obj.error)
                    # TOGGLE
                    elif obj.type == 'toggle':
                        if obj.can_use(self, objects, objects2, objects3):
                            game.sound_toggle.play()
                            self.check_swaps(obj, game)
                            if obj.anim == 'idle':
                                obj.set_anim('on')
                                game.message(self.rect.x, self.rect.y - self.height, obj.response)
                            else:
                                obj.set_anim('idle')
                                game.message(self.rect.x, self.rect.y - self.height, obj.message)
                        else:
                            if obj.breaks and obj.anim == 'on':
                                game.sound_toggle.play()
                                game.message(self.rect.x, self.rect.y - self.height, obj.response)
                            else:
                                game.sound_etoggle.play()
                                game.message(self.rect.x, self.rect.y - self.height, obj.error)
                    # NPC
                    elif obj.type == 'npc':
                        if obj.can_use(self, objects, objects2, objects3):
                            game.sound_enpc.play()
                            self.check_swaps(obj, game)
                            if self.rect.centery < 300:
                                game.message(self.rect.x, self.rect.centery + self.rect.height*.5, obj.message)
                            else:
                                game.message(self.rect.x, self.rect.centery - self.rect.height - 40, obj.message)
                        else:
                            game.sound_npc.play()
                            if self.rect.centery < 300:
                                game.message(self.rect.x, self.rect.centery + self.rect.height, obj.error)
                            else:
                                game.message(self.rect.x, self.rect.centery - self.rect.height - 40, obj.error)
                    # DOOR
                    elif obj.type == 'door':
                        if obj.can_use(self, objects, objects2, objects3):
                            game.sound_door.play()
                            self.check_swaps(obj, game)
                            game.message(self.rect.x, self.rect.y - self.height/2, obj.response)
                            game.world, game.loc = obj.to

                            self.rect.centerx = 400
                            self.rect.bottom = 490
                            break
                        else:
                            game.message(self.rect.x, self.rect.y - self.height/2, obj.error)

    def add_swap(self, f, t, at):
        if not self.swaps.has_key(at):
            self.swaps[at] = {'from':f, 'to':t}
        else:
            self.swaps[at].append({'from':f, 'to':t})

    def check_swaps(self, obj, game):
        if self.swaps.has_key(obj.name):
            for item in self.swaps[obj.name]['from']:
                if not self.inventory.has_key(item):
                    return
            for item in self.swaps[obj.name]['from']:
                self.use_item(item, game)
            for item in self.swaps[obj.name]['to'][0]:
                newitem = pygame.image.load(os.path.join('assets', item + '_inv.png'))
                self.inventory[item] = {'image': newitem, 'uses': self.swaps[obj.name]['to'][1]}
                game.message(self.rect.x, self.rect.y - self.height/2, "sweet/"+item)


    def draw_inv(self, display):
        slot = 0
        w = 50
        for item in self.inventory:
            h = self.inventory[item]['image'].get_height()
            display.blit(self.inventory[item]['image'], (w*slot+10, 0, w, h))
            slot += 1

    def use_item(self, name, game):
        self.inventory[name]['uses'] -= 1
        if self.inventory[name]['uses'] <= 0:
            item = self.inventory.pop(name)

class Game:
    def setup_images(self, world, num):
        self.bg[world] = []
        self.restr.append({})
        for i in range(0, num):
            newimage = pygame.image.load(os.path.join('assets', 'bg_'+str(world)+'_'+str(i)+'.png'))
            self.bg[world].append(newimage)
            self.add_restr(world, i) # set no restrictions by default

    def add_restr(self, world, loc, left=0, right=0, top=0, bot=0):
        self.restr[world][loc] = {'left':left, 'right':self.width-right, 'top':top, 'bot':self.height-bot}

    def message(self, x, y, msg):
        self.messages = []
        self.timer = 0.0
        msgs = msg.split('/')
        for i in range(0, len(msgs)):
            text = self.font.render(msgs[i], 0, (50,50,50))
            self.messages.append([text, (x, y+i*(self.font_size))])

    def message_timer(self, dt):
        if self.timer < self.timer_max:
            self.timer += dt
        else:
            self.messages = []

    def main(self):
        self.width, self.height = (800, 600)
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('disconnected worlds')
        clock = pygame.time.Clock()
        fps = 60

        # setup font and messages
        self.messages = []
        self.timer_max = 60.0
        self.timer = self.timer_max
        self.font_size = 32
        self.font = pygame.font.Font(os.path.join('misc', 'Before the sun rises.ttf'), self.font_size)
        self.font_width_max = self.width * 0.3

        pygame.mixer.init()
        pygame.mixer.music.load(os.path.join('misc', 'above.ogg'))
        pygame.mixer.music.play(-1)
        self.sound_enpc = pygame.mixer.Sound(os.path.join('misc', 'npc.wav'))
        self.sound_npc = pygame.mixer.Sound(os.path.join('misc', 'e_npc.wav'))
        self.sound_npc.set_volume(0.8)
        self.sound_pickup = pygame.mixer.Sound(os.path.join('misc', 'pickup.wav'))
        self.sound_etoggle = pygame.mixer.Sound(os.path.join('misc', 'e_toggle.wav'))
        self.sound_toggle = pygame.mixer.Sound(os.path.join('misc', 'toggle.wav'))
        self.sound_door = pygame.mixer.Sound(os.path.join('misc', 'door.wav'))


        self.player = Player('player', 'player.png', 128, 200)
        self.player.set_pos(200, 300)
        self.player.setup_frames('idle', 0, 3)
        self.player.setup_frames('up', 1, 3)
        self.player.setup_frames('right', 2, 3)
        self.player.setup_frames('left', 3, 3)

        self.p_bucket = Object('bucket', 'bucket.png', 97, 138)
        self.p_bucket.set_pos(117, 392)
        self.p_bucket.set_view(0, 0)
        self.p_bucket.set_type('pickup')
        self.p_bucket.set_messages(message="oh cool/a bucket")

        self.d_arch = Object('arch', 'arch.png', 200, 252)
        self.d_arch.set_pos(295, 115)
        self.d_arch.set_view(0, 0)
        self.d_arch.set_type('door', (1,0))

        self.p_nail = Object('nail', 'nail.png', 50, 139)
        self.p_nail.set_pos(584, 189)
        self.p_nail.set_view(0, 0)
        self.p_nail.set_type('pickup')
        self.p_nail.set_messages(message='this is a rather/large nail')

        self.d_archexit = Object('archexit', 'archexit.png', 269, 203)
        self.d_archexit.set_pos(100, 398)
        self.d_archexit.set_view(1, 0)
        self.d_archexit.set_type('door', (0,0))

        self.t_firebreather = Object('firebreather', 'firebreather.png', 359, 320)
        self.t_firebreather.set_pos(441, 130)
        self.t_firebreather.set_view(1, 0)
        self.t_firebreather.set_type('toggle')
        self.t_firebreather.add_req('match')
        self.t_firebreather.set_messages(error='"fire fire fire?"', response='"thanks thanks thanks"')
        self.t_firebreather.setup_frames('on', 1, 2)

        self.n_cow = Object('cow', 'cow.png', 277, 244)
        self.n_cow.set_pos(180, 60)
        self.n_cow.set_view(0, 1)
        self.n_cow.set_type('npc')
        self.n_cow.set_messages(message='"moo"')

        self.n_cowguy = Object('cowguy', 'cowguy.png', 166, 319)
        self.n_cowguy.set_pos(510, 140)
        self.n_cowguy.set_view(0 ,1)
        self.n_cowguy.set_type('npc')
        self.n_cowguy.add_req('milk')
        self.n_cowguy.set_messages(error='"i have no/jars left"', message='"they say hot milk/will make anyone/fall asleep"')

        self.p_coin = Object('coin', 'coin.png', 83, 52)
        self.p_coin.set_pos(200, 500)
        self.p_coin.set_view(0, 2)
        self.p_coin.set_type('pickup')
        self.p_coin.set_messages(message='i should return this...')

        self.d_shopdoor = Object('shopdoor', 'shopdoor.png', 62, 121)
        self.d_shopdoor.set_pos(100, 120)
        self.d_shopdoor.set_view(0, 2)
        self.d_shopdoor.set_type('door', (2, 0))

        self.n_shopman = Object('shopman', 'shopman.png', 145, 202)
        self.n_shopman.set_pos(120, 20)
        self.n_shopman.set_view(2, 0)
        self.n_shopman.set_type('npc')
        self.n_shopman.set_messages(message='"hmph!"')

        self.d_shopmat = Object('shopmat', 'mat.png', 209, 84)
        self.d_shopmat.set_pos(250, 500)
        self.d_shopmat.set_view(2, 0)
        self.d_shopmat.set_type('door', (0, 2))

        self.p_shoprope = Object('rope', 'shoprope.png', 120, 270)
        self.p_shoprope.set_pos(650, 180)
        self.p_shoprope.set_view(2, 0)
        self.p_shoprope.set_type('pickup')
        self.p_shoprope.set_messages(message="neato/some rope")

        self.p_match = Object('match', 'match.png', 41, 103)
        self.p_match.set_pos(530, 35)
        self.p_match.set_view(2, 0)
        self.p_match.set_type('pickup')
        self.p_match.add_req('coin')
        self.p_match.set_uses(100)
        self.p_match.set_messages(message="i don't want/to set the world/on fire")

        self.n_reader = Object('reader', 'reader.png', 50, 137)
        self.n_reader.set_pos(300, 130)
        self.n_reader.set_view(0, 3)
        self.n_reader.set_type('npc')
        self.n_reader.set_messages(message='"that guy is/a snob"', error='"woah/that hole/is scary"')

        self.t_ropenail = Object('ropenail', 'ropenail.png', 84, 121)
        self.t_ropenail.set_pos(640, 370)
        self.t_ropenail.set_view(0, 3)
        self.t_ropenail.set_type('toggle')
        self.t_ropenail.add_req('nail')
        self.t_ropenail.add_req('rope')
        #self.t_ropenail.add_unreq('cardboard')
        self.t_ropenail.setup_frames('on', 1, 2)
        self.t_ropenail.set_messages(response="down i go/i do suppose", message="down i go/i do suppose", error="the ground here/looks soft")

        self.t_hipster = Object('hipster', 'hipster.png', 323, 190)
        self.t_hipster.set_pos(370, 350)
        self.t_hipster.set_view(0, 3)
        self.t_hipster.set_type('use')
        self.t_hipster.add_req('hotmilk')
        self.t_hipster.set_messages(error='"i cant/*yawn*/let you in/*yawn*"', message='"zzz..."')

        #self.t_cardboard = Object('cardboard', 'cardboard.png', 375, 235)
        #self.t_cardboard.set_pos(300, 250)
        #self.t_cardboard.set_view(0, 3)
        #self.t_cardboard.set_type('toggle')
        #self.t_cardboard.add_req('match')
        #self.t_cardboard.add_parent('hipster')
        #self.t_cardboard.set_breaks()
        #self.t_cardboard.set_messages(message="cardboard burns quickly")

        self.d_hole = Object('hole', 'hole.png', 105, 48)
        self.d_hole.set_pos(540, 450)
        self.d_hole.set_view(0, 3)
        self.d_hole.set_type('door', (3,0))
        #self.d_hole.add_parent('cardboard')
        self.d_hole.add_parent('ropenail')
        self.d_hole.set_messages(error="it's a long/way down")

        self.n_red = Object('red', 'red.png', 177, 207)
        self.n_red.set_pos(500, 350)
        self.n_red.set_view(3, 0)
        self.n_red.set_type('npc')
        self.n_red.add_parent('light')
        self.n_red.set_messages(error='"hey! nice to/ meet you,/but please close/that damn hole"', message='"cardboard wants me/to thank you/for playing!"')

        self.d_ldoor = Object('ldoor', 'ldoor.png', 108, 248)
        self.d_ldoor.set_pos(150, 190)
        self.d_ldoor.set_view(3, 0)
        self.d_ldoor.set_type('door', (4,0))

        self.t_light = Object('light', 'light.png', 137, 517)
        self.t_light.set_pos(300, -30)
        self.t_light.set_view(3, 0)
        self.t_light.set_type('toggle')
        self.t_light.add_req('fullballoon')
        self.t_light.setup_frames('on', 1, 2)
        self.t_light.set_messages(error="it seems i have/turned on the lights", message="wow/i have good aim")

        self.n_record = Object('record', 'record.png', 171, 197)
        self.n_record.set_pos(200, 200)
        self.n_record.set_view(4, 0)
        self.n_record.set_type('npc')
        self.n_record.set_messages(message='i think i have/heard this song/before')

        self.d_recordexit = Object('recordexit', 'mat.png', 209, 84)
        self.d_recordexit.set_pos(250, 500)
        self.d_recordexit.set_view(4, 0)
        self.d_recordexit.set_type('door', (3, 0))

        self.n_green = Object('green', 'green.png', 161, 319)
        self.n_green.set_pos(400, 250)
        self.n_green.set_view(4, 1)
        self.n_green.set_type('npc')
        self.n_green.add_req('balloon')
        self.n_green.set_messages(error='it is just/sitting there/blowing air', message='"there you go friend"')

        self.n_blue = Object('blue', 'blue.png', 137, 371)
        self.n_blue.set_pos(175, 180)
        self.n_blue.set_view(4, 2)
        self.n_blue.set_type('npc')
        self.n_blue.set_messages(error='"i love balloons!"', message='"nice balloon!"')
        self.n_blue.add_req('balloon')

        self.p_balloon = Object('balloon', 'balloon.png', 85, 48)
        self.p_balloon.set_pos(500, 400)
        self.p_balloon.set_view(4, 2)
        self.p_balloon.set_type('pickup')
        self.p_balloon.set_messages(message="i might be/able to use this/for something")



        self.objects = pygame.sprite.Group()
        self.objects2 = pygame.sprite.Group()
        self.objects3 = pygame.sprite.Group()

        # ADD OBJECTS TO THE OBJECT GROUP
        # 0,0
        self.objects.add(self.p_bucket)
        self.objects.add(self.d_arch)
        self.objects.add(self.p_nail)
        # 1,0
        self.objects.add(self.d_archexit)
        self.objects.add(self.t_firebreather)
        # 0,1
        self.objects.add(self.n_cow)
        self.objects.add(self.n_cowguy)
        # 0,2
        self.objects.add(self.p_coin)
        self.objects.add(self.d_shopdoor)
        # 2,0
        self.objects.add(self.n_shopman)
        self.objects.add(self.d_shopmat)
        self.objects.add(self.p_shoprope)
        self.objects.add(self.p_match)
        # 0,3
        self.objects.add(self.n_reader)
        self.objects.add(self.d_hole)
        self.objects3.add(self.t_hipster)
        self.objects3.add(self.t_ropenail)
        #self.objects2.add(self.t_cardboard)
        # 3,0
        self.objects.add(self.n_red)
        self.objects.add(self.t_light)
        self.objects.add(self.d_ldoor)
        # 4,0
        self.objects.add(self.n_record)
        self.objects.add(self.d_recordexit)
        # 4,1
        self.objects.add(self.n_green)
        # 4,2
        self.objects.add(self.n_blue)
        self.objects.add(self.p_balloon)


        self.bg = {}
        self.restr = []
        self.world = 0
        self.loc = 3
        self.setup_images(0, 4) # world 0, 4 imgages
        self.setup_images(1, 1) # world 1, 1 image
        self.setup_images(2, 1) # world 2, 1 image
        self.setup_images(3, 1) # world 3, 1 image
        self.setup_images(4, 3) # world 4, 3 image
        self.rect = pygame.Rect(0,0,self.width,self.height)

        # setup restrictions for each view&world
        self.add_restr(0, 0, top=200, left=100)
        self.add_restr(0, 1, top=200)
        self.add_restr(0, 2, top=200)
        self.add_restr(0, 3, top=200, right=100)
        self.add_restr(1, 0, top=200)
        self.add_restr(2, 0, top=200)
        self.add_restr(3, 0, top=450, left=100, right=50, bot=100)
        self.add_restr(4, 0, top=200, left=100)
        self.add_restr(4, 1, top=420, bot=100)
        self.add_restr(4, 2, top=200, right=100)

        self.player.add_swap(['bucket'], [['milk'], 1], 'cow')
        self.player.add_swap(['milk'], [['hotmilk'], 1], 'firebreather')
        self.player.add_swap(['balloon'], [['fullballoon'], 1], 'green')

        while 1:
            dt = clock.tick(fps)
            dt = dt / 50.0

            keys = pygame.key.get_pressed()

            self.player.move(dt, keys, self.restr[self.world][self.loc])

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        self.player.interact(self, self.objects3, self.objects, self.objects2)
                        self.player.interact(self, self.objects2, self.objects, self.objects3)
                        self.player.interact(self, self.objects, self.objects2, self.objects3)
#               if event.type == pygame.KEYUP:
#                    if event.key == pygame.K_LEFT or event.key == pygame.K_s\
#                    or event.key == pygame.K_RIGHT or event.key == pygame.K_f\
#                    or event.key == pygame.K_UP or event.key == pygame.K_d\
#                    or event.key == pygame.K_DOWN or event.key == pygame.K_e:
#                        self.player.set_anim('idle')

            self.loc = (self.loc + self.player.change_view(self.width, self.bg[self.world])) % len(self.bg[self.world])

            # draw world
            self.screen.blit(self.bg[self.world][self.loc], self.rect)
            # draw objects
            for obj in self.objects:
                obj.animate(dt)
                obj.draw(self.screen, self.world, self.loc)
            for obj in self.objects2:
                obj.animate(dt)
                obj.draw(self.screen, self.world, self.loc)
            for obj in self.objects3:
                obj.animate(dt)
                obj.draw(self.screen, self.world, self.loc)
            # draw player
            self.player.animate(dt)
            self.player.draw(self.screen, self.world, self.loc)
            # draw messages
            self.message_timer(dt)
            for msg in self.messages:
                self.screen.blit(msg[0], msg[1])
            # draw inventory
            self.player.draw_inv(self.screen)
            # update screen
            pygame.display.flip()


if __name__=='__main__':
    pygame.init()
    Game().main()