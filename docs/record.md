  python src/train_improved.py \
      --train_dir data/fan/train \
      --machine_type fan \
      --patch_frames 128 \          # 从64→128（4秒音频）
      --use_specaugment \            # 开启SpecAugment
      --epochs 150 \                 # 更多epoch
      --label_smoothing 0.1 \        # 防过拟合
      --dropout_rate 0.3 \           # 更强正则
      --scheduler cosine 


python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 128 --batch_size 32 --epochs 100 --dropout_rate 0.3 --weight_decay 1e-4 --scheduler cosine

结果为0.64 - 0.66


python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 128 --batch_size 32 --epochs 100 --dropout_rate 0.2 --weight_decay 1e-5 --scheduler cosine 

结果为 0.67


python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 64 --batch_size 64 --epochs 150 --dropout_rate 0.2 --weight_decay 1e-5 --scheduler cosine

结果为0.7259 - 0.7274

 python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 64 --batch_size 64 --epochs 200 --dropout_rate 0.2 --weight_decay 1e-5 --scheduler cosine --no-augmentation  

 结果为0.67

 python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 64 --batch_size 64 --epochs 150 --dropout_rate 0.2 --weight_decay 1e-5 --optimizer adamw --lr 1e-4 --scheduler cosine --warmup_epochs 5

 结果为0.69

 python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 64 --batch_size 64 --epochs 150 --dropout_rate 0.2 --weight_decay 1e-5 --optimizer adamw --lr 5e-4 --scheduler cosine --warmup_epochs 5

 结果为0.678

 python src/train.py --train_dir data/fan/train --machine_type fan --patch_frames 64 --batch_size 64 --epochs 150 --dropout_rate 0.2 --weight_decay 1e-5 --optimizer adam --lr 1e-3 --scheduler cosine --warmup_epochs 5

 结果为0.7277 

 python src/train_test.py train --backbone resnet34 --pretrained --train_dir data/fan/train --machine_type fan --patch_frames 96 --batch_size 32 --epochs 150 --dropout_rate 0.3 --weight_decay 1e-4 --optimizer adamw --lr 5e-4 --scheduler cosine --warmup_epochs 5 --seed 42

 结果为0.67


D:\baseline> python src/train.py --train_dir data/pump/train --machine_type pump --patch_frames 64 --batch_size 64 --epochs 150 --dropout_rate 0.2 --weight_decay 1e-5 --optimizer adam --lr 1e-3 --scheduler cosine --warmup_epochs 5
