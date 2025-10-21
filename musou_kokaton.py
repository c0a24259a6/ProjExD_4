import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface,score: "Score"):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        引数3 score:現在のスコア
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
        self.image = self.imgs[self.dire]
        # 発動条件（右Shiftキーが押され、スコアが100より大きい）
        if key_lst[pg.K_RSHIFT] and score.value > 100 and self.state == "normal":
            self.state = "hyper"
            self.hyper_life = 500  # 発動時間を500フレームに設定
            score.value -=  100         # スコアを100消費
         # 無敵状態の処理
        if self.state == "hyper":
            self.hyper_life -= 1  # 残り時間を1減らす
            if self.hyper_life < 0:
                self.state = "normal"  # 時間が来たら通常状態に戻す
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
        screen.blit(self.image, self.rect)
    

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.inactive = False  # EMPで無効化されるとTrueになる

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: int = 0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        angle += angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam(pg.sprite.Sprite):
    """
    ネオビームに関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        引数1 bird：ビームを放つこうかとん
        引数2：num：ビームの数
        """
        super().__init__()
        self.bird = bird
        self.num = num
        

    def gen_beams(self):
        neobeam = []
        for i in range(-50, +51, int(50/(self.num//2))):
            neobeam.append(Beam(self.bird, i))
        return neobeam


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.disabled_by_emp = False  # EMP無効化されたかどうか


    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP(pg.sprite.Sprite):
    """
    発動時に存在する敵機と爆弾を無効化するクラス
    発動時に存在する Enemy と Bomb を無効化する。
    表示は画面全体に透過黄色矩形を表示
    """
    def __init__(self, emy_group: pg.sprite.Group, bomb_group: pg.sprite.Group, screen: pg.Surface, life_frames: int = 3):
        super().__init__()
        surf = pg.Surface((WIDTH, HEIGHT), flags=pg.SRCALPHA)
        surf.fill((255, 255, 0, 100))  # 透過黄色
        self.image = surf
        self.rect = self.image.get_rect()
        self.life = life_frames

        # EMP効果：敵と爆弾を無効化
        for emy in list(emy_group):
            emy.interval = math.inf   # 爆弾を落とさなくする
            emy.disabled_by_emp = True
            emy.image = pg.transform.laplacian(emy.image) #見た目ラプラシアンフィルタ

        for bomb in list(bomb_group):
            bomb.speed /= 2           # 速度半減
            bomb.inactive = True      # 起爆無効化
    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()



class Shield(pg.sprite.Sprite):
    """
    防御壁の設定に関するクラス
    こうかとんの向きに合わせた防御壁
    防御壁のサイズ
    """
    def __init__(self,bird,life=400):
        super().__init__()
        # 壁の大きさ（こうかとんの2倍の高さ）
        w, h = 20, bird.rect.height * 2
        self.image = pg.Surface((w, h))
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, w, h))
        #こうかとんの向き
        vx, vy = bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()

        # 向いている方向に1体分ずらして配置
        kouka_x = bird.rect.centerx + vx * bird.rect.width
        kouka_y = bird.rect.centery + vy * bird.rect.height
        self.rect.center = (kouka_x, kouka_y)

        self.life = life

    def update(self):   
        self.life -= 1
        if self.life < 0:
            self.kill() #防御壁を削除する

class Gravity(pg.sprite.Sprite):

    def __init__(self,life=400):
        super().__init__()
        self.life=life
        self.image = pg.Surface((WIDTH,HEIGHT))
        pg.draw.rect(self.image,(0,0,0),pg.Rect(0,0,WIDTH,HEIGHT))
        self.image.set_alpha(150)
        self.rect = self.image.get_rect()

    def update(self):
            self.life-=1
            if self.life<0:
                self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emps = pg.sprite.Group()  # EMPの表示用グループ
    

    gravity = pg.sprite.Group()
    shields = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if key_lst[pg.K_LSHIFT] and key_lst[pg.K_SPACE]:
                beams.add(NeoBeam(bird, 5).gen_beams())
            elif event.type == pg.KEYDOWN and event.key == pg.K_SPACE and key_lst[pg.K_LSHIFT] != True:
                beams.add(Beam(bird))
                        # EMP発動（追加）
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                # スコア20点以上で発動
                if score.value > 20 and len(emps) == 0:
                    score.value -= 20  # スコア消費
                    # 表示フレーム数を指定して追加
                    life_frames = max(1, int(0.05 * 50)) 
                    emps.add(EMP(emys, bombs, screen, life_frames))

            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                # スコアが200より大きく、かつ重力場が発動していない
                if score.value > 200 and len(gravity) == 0:
                    score.value -= 200  #スコアを200消費
                    gravity.add(Gravity())
                 
        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(beams, bombs, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        if len(gravity) > 0:  # 重力場が発動中の場合
    
            for bomb in pg.sprite.groupcollide(bombs, gravity, True, False).keys():
                exps.add(Explosion(bomb, 50))  
                score.value += 1  # 1点アップ

            for emy in pg.sprite.groupcollide(emys, gravity, True, False).keys():
                exps.add(Explosion(emy, 100))  
                score.value += 10  # 10点アップ
                bird.change_img(6, screen)

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            # EMPで無効化された爆弾は何も起こさず消える
            if getattr(bomb, "inactive", False):
                continue
            # 通常の被弾処理（ゲームオーバー）
            # hyper状態(無敵状態)の場合
            if bird.state == "hyper":
                exps.add(Explosion(bomb,50)) # 爆発エフェクト
                score.value += 1 # 1点アップ
            else:
                bird.change_img(8, screen)
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
                

         


        
        emps.update()
        emps.draw(screen)

        bird.update(key_lst, screen, score)     
        """
        防御壁発動
        """
        key_lst = pg.key.get_pressed()
        if key_lst[pg.K_s] and score.value > 50 and len(shields) == 0:
            score.value -= 50
            shields.add(Shield(bird))

        """
        防御壁と爆弾の衝突処理
        """
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
        shields.draw(screen)
        shields.update()
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        gravity.update()
        gravity.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
    
 