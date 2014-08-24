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
            display.blit(self.frames[self.anim][self.frame], self.rect)

    def set_anim(self, name):
        self.frame = 0
        self.frametime = 0
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

    def can_use(self, player, objects):
        r = []
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
                if not(obj.name == parent and obj.anim == 'on'):
                    return False

        for req in r:
            player.inventory[req]['uses'] -= 1
            if player.inventory[req]['uses'] <= 0:
                player.inventory.pop(req)
        if self.breaks:
            self.reqs = ['global warming'] # because it doesn't exist lol
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

    def move(self, dt, keys, restr):
        if (keys[pygame.K_LEFT] or keys[pygame.K_s]) and self.rect.centerx > restr['left']:
            self.rect = self.rect.move(-self.xspeed * dt, 0)
            self.set_anim('left')
        if (keys[pygame.K_RIGHT] or keys[pygame.K_f]) and self.rect.centerx < restr['right']:
            self.rect = self.rect.move(self.xspeed * dt, 0)
            self.set_anim('right')
        if (keys[pygame.K_UP] or keys[pygame.K_e]) and self.rect.bottom > restr['top']:
            self.rect = self.rect.move(0, -self.yspeed * dt)
            self.set_anim('up')
        if (keys[pygame.K_DOWN] or keys[pygame.K_d]) and self.rect.bottom < restr['bot']:
            self.rect = self.rect.move(0, self.yspeed * dt)
            self.set_anim('idle')

    def change_view(self, width, world):
        if len(world) != 1:
            if self.rect.centerx < self.view_border:
                self.set_pos(450, self.rect.y)
                return -1
            if self.rect.centerx > width - self.view_border:
                self.set_pos(200, self.rect.y)
                return 1
        return 0

    def interact(self, game, objects):
        for obj in objects:
            if self.rect.colliderect(obj.rect) and (game.world == obj.view[0] and game.loc == obj.view[1]):
                # PICKUP
                if obj.type == 'pickup' or obj.type == 'use':
                    if obj.can_use(self, objects): # pickup the object
                        if obj.type == 'pickup':
                            new_item = pygame.image.load(os.path.join('assets', obj.name+'_inv'+'.png'))
                            self.inventory[obj.name] = {'image': new_item, 'uses': obj.uses}
                        game.message(self.rect.centerx, self.rect.y - self.height/2, obj.message)
                        objects.remove(obj)
                    else:
                        game.message(self.rect.centerx, self.rect.y - self.height/2, obj.error)
                # TOGGLE
                elif obj.type == 'toggle': 
                    if obj.can_use(self, objects):
                        if obj.anim == 'idle':
                            obj.set_anim('on')
                            game.message(self.rect.centerx, self.rect.y - self.height/2, obj.response)
                        else:
                            obj.set_anim('idle')
                            game.message(self.rect.centerx, self.rect.y - self.height/2, obj.message)
                    else:
                        game.message(self.rect.centerx, self.rect.y - self.height/2, obj.error)
                # NPC
                elif obj.type == 'npc':
                    if obj.can_use(self, objects):
                        game.message(obj.rect.centerx, obj.rect.centery - obj.rect.height, obj.message)
                    else:
                        game.message(obj.rect.centerx, obj.rect.centery - obj.rect.height, obj.error)               
                # DOOR
                elif obj.type == 'door':
                    if obj.can_use(self, objects):
                        game.message(self.rect.centerx, self.rect.y - self.height/2, obj.response)
                        game.world, game.view = obj.to
                    else:
                        game.message(self.rect.centerx, self.rect.y - self.height/2, obj.error)

    def draw_inv(self, display):
        slot = 0
        for item in self.inventory:
            w, h = self.inventory[item]['image'].get_width(), self.inventory[item]['image'].get_height()
            display.blit(self.inventory[item]['image'], (w*slot, 0, w, h))
            slot += 1

    def use_item(self, name):
        item = self.inventory.pop(name)
        game.message(self.rect.centerx, self.rect.centery - self.width*.5, item.response)

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

        #pygame.mixer.init()
        #pygame.mixer.music.load(os.path.join('music', 'music.ogg'))
        #pygame.mixer.music.play()

        self.player = Player('player', 'player.png', 128, 200)
        self.player.set_pos(500, 300)
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
        self.d_arch.set_messages(response="this place is neat")

        self.p_nail = Object('nail', 'nail.png', 50, 139)
        self.p_nail.set_pos(584, 189)
        self.p_nail.set_view(0, 0)
        self.p_nail.set_type('pickup')
        self.p_nail.set_messages(message='this is a rather/large nail')

        self.objects = pygame.sprite.Group()

        self.objects.add(self.p_bucket)
        self.objects.add(self.d_arch)
        self.objects.add(self.p_nail)

        self.bg = {}
        self.restr = []
        self.world = 0
        self.loc = 0
        self.setup_images(0, 4) # world 0, 4 imgages
        self.setup_images(1, 1) # world 1, 1 image
        self.setup_images(2, 1) # world 1, 1 image
        self.setup_images(3, 1) # world 1, 1 image
        self.setup_images(4, 2) # world 1, 1 image
        self.setup_images(5, 1) # world 1, 1 image
        self.rect = pygame.Rect(0,0,self.width,self.height)

        # setup restrictions for each view&world
        self.add_restr(0, 0, top=200, left=100)
        self.add_restr(0, 1, top=200)
        self.add_restr(0, 2, top=200)
        self.add_restr(0, 3, top=200, right=100)

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
                        self.player.interact(self, self.objects)
#               if event.type == pygame.KEYUP:
#                    if event.key == pygame.K_LEFT or event.key == pygame.K_s\
#                    or event.key == pygame.K_RIGHT or event.key == pygame.K_f\
#                    or event.key == pygame.K_UP or event.key == pygame.K_d\
#                    or event.key == pygame.K_DOWN or event.key == pygame.K_e:
#                        self.player.set_anim('idle')
#                        print('fuckkk')


            self.loc = (self.loc + self.player.change_view(self.width, self.bg[self.world])) % len(self.bg[self.world])

            # draw world
            self.screen.blit(self.bg[self.world][self.loc], self.rect)
            # draw objects
            for obj in self.objects:
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