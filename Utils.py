import pygame
import sys
from math import sqrt
import time

SCREENWIDTH = 720
SCREENHEIGHT = 480
FPS = 60

# pygame.mixer.pre_init(44100, -16,2)
pygame.init()

screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
# screen = pygame.display.set_mode((1366, 768))

pygame.display.set_caption("Chopper Attack")
GAME_FONT = pygame.font.SysFont('Comic Sans MS', 30)


def score(points):
    over_font = pygame.font.Font('freesansbold.ttf', 10)
    over_text = over_font.render("Points : " + str(points), True, (255, 255, 255))
    screen.blit(over_text, (0, 0))

def GetCurrentTime():
    return pygame.time.get_ticks()


def LoadGraphic(path):
    return pygame.image.load(path).convert_alpha()


def Collides(elementA, elementB):
    return pygame.sprite.collide_rect(elementA, elementB)


class Helicopter(pygame.sprite.Sprite):
    DoNothing = 0
    Up = 1
    Down = 2

    def moveUp(self):
        self.rect.centery += self.speed * -1
        if self.rect.top <= 0: self.rect.top = 0

    def moveDown(self):
        self.rect.centery += self.speed * 1
        if self.rect.bottom >= SCREENHEIGHT: self.rect.bottom = SCREENHEIGHT

    def shoot(self):
        if self.delegate and hasattr(self.delegate, "heliFired"):
            self.delegate.heliFired(self)

    def isDead(self):
        return self.health <= 0

    def takeDamage(self, damage=10):
        damage = abs(damage)
        self.health -= damage
        if self.delegate and hasattr(self.delegate, "heliTookDamage"):
            self.delegate.heliTookDamage(self, damage)

    def update(self, action):  # delta, action):
        pygame.event.pump()
        # reward = 0 # If no actions were selected, stick to 0

        if self.isDead(): return

        # Perform Actions
        if action[Helicopter.Up]:  # If we're doing nothing
            print("PLAYER moving up")
            self.moveUp()

        if action[Helicopter.Down]:
            print("PLAYER moving down")
            self.moveDown()

        if len(action) > 3: print("Wtf, that's wrong...")

    # A static method is exactly like a function, but it just belongs to a class
    # It's like in the class's "namespace", like in C++, meaning you have to use
    # the class name to call it ( Helicopter.Config(...) )
    @staticmethod
    def Config(graphic, position, direction, speed=10, name="N/A", health=100):
        config = dict()  # or {}

        config["graphic"] = graphic
        config["position"] = position
        config["direction"] = direction
        config["health"] = health
        config["speed"] = speed
        config["name"] = name

        return config

    def __init__(self, config):
        pygame.sprite.Sprite.__init__(self)

        self.name = config["name"]

        self.direction = config["direction"]
        self.speed = config["speed"]

        self.image = LoadGraphic(config["graphic"])
        self.rect = self.image.get_rect()

        self.rect.center = config["position"].xy()

        self.health = config["health"]
        self.delegate = None

        self.lastConfig = config


class EnemyHelicopter(Helicopter):
    def update(self, actions):
        if self.target.rect.top < self.rect.centery < self.target.rect.bottom:
            if self.timeToFire == 0:
                print(self.name + " shooting!")
                self.shoot()
                self.timeToFire = self.limit
            else:
                self.timeToFire -= 1


        elif self.rect.centery > self.target.rect.centery:
            print("Moving enemy up")
            self.moveUp()

        elif self.rect.centery < self.target.rect.centery:
            print("Moving enemy down")
            self.moveDown()

    def __init__(self, config, target, limit=20):
        Helicopter.__init__(self, config)
        self.target = target
        self.limit = limit
        self.timeToFire = limit


class Projectile(pygame.sprite.Sprite):
    def __init__(self, damage, position, direction, speed=15):
        pygame.sprite.Sprite.__init__(self)
        self.image = LoadGraphic("images/bullet.png")
        self.rect = self.image.get_rect()
        self.rect.center = position.xy()
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.used = False

    def done(self):
        outLeft = self.rect.centerx < 0
        outRight = self.rect.centerx > SCREENWIDTH
        return outLeft or outRight or self.used

    def use(self):
        self.used = True
        return self.damage

    def update(self):
        oldPosition = vector2(self.rect.center)
        newPosition = oldPosition.add(self.direction.scale(self.speed))
        self.rect.center = newPosition.xy()


class GameState:
    def frame_step(self, actions):
        time.sleep(1.0 / FPS)

        # Reset the screen to black, otherwise
        # the old image is left behind.
        screen.fill((0, 0, 0))

        # The variable below denotes the amount of points
        # earned by the player for certain actions.
        # It's possible to gain negative points by doing
        # something completely stupid.
        self.reward = 0

        # Update the projectiles of the world
        self.projectiles.update()

        # Update the players
        self.players.update(actions)

        # Check for projectile collisions
        self.checkForCollisions()

        # Draw the players
        self.players.draw(screen)

        # Draw the projectiles over players
        self.projectiles.draw(screen)

        # Update the screen to redraw the new content.
        pygame.display.update()
        image = pygame.surfarray.array3d(pygame.display.get_surface())

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.display.quit(), sys.exit()

        if self.player.isDead():
            self.__init__()
            self.reward = -1

        return image, self.reward, self.player.isDead()

    def checkForCollisions(self):
        for projectile in self.projectiles.sprites():
            for player in self.players.sprites():
                if Collides(projectile, player):
                    player.takeDamage(projectile.use())
                    print("Hit " + player.name)

            if projectile.done():
                if not projectile.used: self.reward += 1
                score(self.bonus)
                self.projectiles.remove(projectile)
                print("Projectile done...")

    def heliFired(self, heli):
        position = vector2(heli.rect.center)

        heliOffset = heli.image.get_width() / 2
        position = position.add(heli.direction.scale(heliOffset))

        projectile = Projectile(100, vector2(0, 0), heli.direction, 25)

        projOffset = projectile.image.get_width() / 2
        position = position.add(heli.direction.scale(projOffset))

        projectile.rect.center = position.xy()

        self.projectiles.add(projectile)

    def heliTookDamage(self, heli, damage):
        self.bonus -= 1

    def __init__(self):
        self.players = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.bonus = 0

        # This is the AI (dynamic actions)
        pGraphic = "images/player.png"
        pPosition = vector2(SCREENWIDTH, SCREENHEIGHT / 2)
        pDirection = vector2(-1, 0)
        pSpeed = 10
        pConfig = Helicopter.Config(pGraphic, pPosition, pDirection, pSpeed)
        self.player = Helicopter(pConfig)
        self.player.delgate = self
        self.player.name = "Player"

        # This is the Enemy (hard coded actions)
        eGraphic = "images/enemy.png"
        ePosition = vector2(0, SCREENWIDTH / 2)
        eDirection = vector2(1, 0)
        eSpeed = 50
        eConfig = Helicopter.Config(eGraphic, ePosition, eDirection, eSpeed)
        self.enemy = EnemyHelicopter(eConfig, self.player)
        self.enemy.delegate = self
        self.enemy.name = "Enemy"

        self.players.add(self.player, self.enemy)


class vector2:

    def __init__(self, x, y=None):
        if not y and isinstance(x, tuple):
            y = x[1]
            x = x[0]

        self.x = x
        self.y = y

    def add(self, other):
        v = vector2(self.x + other.x, self.y + other.y)
        return v

    def subtract(self, other):
        v = vector2(self.x - other.x, self.y - other.y)
        return v

    def scale(self, scalar):
        v = vector2(self.x * scalar, self.y * scalar)
        return v

    def magnitude(self):
        return sqrt((self.x * self.x) + (self.y * self.y))

    def unitVec(self, magnitude):
        v = vector2(self.x / magnitude, self.y / magnitude)
        return v

    def normalize(self):
        # type: () -> object
        if self.magnitude() == 0:
            return vector2(0, 0)
        else:
            v = vector2(self.x / self.magnitude(), self.y / self.magnitude())
            return v

    def xy(self):
        return (self.x, self.y)

    def checkIfReached(self, otherVec, dirVec):
        if dirVec.x == 0 and dirVec.y < 0 and self.y < otherVec.y:
            return True
        elif dirVec.x == 0 and dirVec.y > 0 and self.y > otherVec.y:
            return True
        elif dirVec.x < 0 and dirVec.y == 0 and self.x < otherVec.x:
            return True
        elif dirVec.x > 0 and dirVec.y == 0 and self.x > otherVec.x:
            return True
        elif dirVec.x > 0 and dirVec.y != 0 and self.x > otherVec.x:
            return True
        elif dirVec.x < 0 and dirVec.y != 0 and self.x < otherVec.x:
            return True
        else:
            return False

    def __str__(self):
        return "({},{})".format(self.x, self.y)
