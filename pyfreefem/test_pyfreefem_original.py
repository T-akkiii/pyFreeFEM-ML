#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_pyfreefem.py
PyFreeFEM繝ｩ繧､繝悶Λ繝ｪ縺ｮ繝・せ繝育畑Python繧ｹ繧ｯ繝ｪ繝励ヨ
"""

import os
import sys
import time
import numpy as np
import logging
from pathlib import Path

# 繧ｫ繝ｬ繝ｳ繝医ョ繧｣繝ｬ繧ｯ繝医Μ繧偵せ繧ｯ繝ｪ繝励ヨ縺ｮ菴咲ｽｮ縺ｫ險ｭ螳・
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

# 繝励Ο繧ｸ繧ｧ繧ｯ繝医Ν繝ｼ繝医ｒ蜿門ｾ励＠縺ｦ繝代せ縺ｫ霑ｽ蜉
project_root = script_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# PyFreeFEM繝ｩ繧､繝悶Λ繝ｪ繧偵う繝ｳ繝昴・繝・
from src.pyfreefem.freefem_interface import FreeFEMInterface
from src.pyfreefem.errors import SharedMemoryError, FreeFEMExecutionError, DataTypeError

# 繝ｭ繧ｬ繝ｼ縺ｮ險ｭ螳・
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_pyfreefem_python.log')
    ]
)
logger = logging.getLogger(__name__)

def test_pyfreefem():
    """PyFreeFEM繝ｩ繧､繝悶Λ繝ｪ縺ｮ蝓ｺ譛ｬ讖溯・繧偵ユ繧ｹ繝医☆繧矩未謨ｰ"""
    logger.info("PyFreeFEM繝・せ繝磯幕蟋・)
    
    try:
        # FreeFEM繧､繝ｳ繧ｿ繝ｼ繝輔ぉ繝ｼ繧ｹ縺ｮ菴懈・
        # 蜈ｱ譛峨Γ繝｢繝ｪ縺ｮ繧ｵ繧､繧ｺ繧・MB縺ｫ險ｭ螳・
        pyff = FreeFEMInterface(shm_name="pyfreefem_shm", shm_size=1024*1024)
        logger.info("FreeFEM繧､繝ｳ繧ｿ繝ｼ繝輔ぉ繝ｼ繧ｹ繧､繝ｳ繧ｹ繧ｿ繝ｳ繧ｹ繧剃ｽ懈・縺励∪縺励◆")
        
        # 蝓ｺ譛ｬ繝・・繧ｿ蝙九・譖ｸ縺崎ｾｼ縺ｿ繝・せ繝・
        # ------------------
        logger.info("繝・・繧ｿ譖ｸ縺崎ｾｼ縺ｿ繝・せ繝磯幕蟋・)
        
        # 謨ｴ謨ｰ蛟､縺ｮ繝・せ繝・
        test_int = 42
        pyff.set_data("test_int", test_int)
        logger.info(f"謨ｴ謨ｰ蛟､繧呈嶌縺崎ｾｼ縺ｿ縺ｾ縺励◆: test_int = {test_int}")
        
        # 豬ｮ蜍募ｰ乗焚轤ｹ蛟､縺ｮ繝・せ繝・
        test_double = 3.14159
        pyff.set_data("test_double", test_double)
        logger.info(f"豬ｮ蜍募ｰ乗焚轤ｹ蛟､繧呈嶌縺崎ｾｼ縺ｿ縺ｾ縺励◆: test_double = {test_double}")
        
        # 譁・ｭ怜・縺ｮ繝・せ繝・
        test_string = "縺薙ｓ縺ｫ縺｡縺ｯ縲￣yFreeFEM!"
        pyff.set_data("test_string", test_string)
        logger.info(f"譁・ｭ怜・繧呈嶌縺崎ｾｼ縺ｿ縺ｾ縺励◆: test_string = {test_string}")
        
        # 驟榊・縺ｮ繝・せ繝・
        test_array = np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float64)
        pyff.set_data("test_array", test_array)
        logger.info(f"驟榊・繧呈嶌縺崎ｾｼ縺ｿ縺ｾ縺励◆: test_array = {test_array}")
        
        # FreeFEM繧ｹ繧ｯ繝ｪ繝励ヨ縺ｮ螳溯｡・
        # ------------------
        logger.info("FreeFEM繧ｹ繧ｯ繝ｪ繝励ヨ螳溯｡後ユ繧ｹ繝磯幕蟋・)
        
        # 繝・せ繝育畑FreeFEM繧ｹ繧ｯ繝ｪ繝励ヨ縺ｮ繝代せ
        freefem_script = os.path.join(project_root, "src", "pyfreefem", "freefem", "test_pyfreefem.edp")
        
        # 繧ｹ繧ｯ繝ｪ繝励ヨ繧貞ｮ溯｡・
        result = pyff.run_script(freefem_script)
        logger.info(f"FreeFEM繧ｹ繧ｯ繝ｪ繝励ヨ縺ｮ螳溯｡檎ｵ先棡: {'謌仙粥' if result.success else '螟ｱ謨・}")
        
        if result.output:
            logger.info(f"蜃ｺ蜉・\n{result.output}")
        
        # FreeFEM縺九ｉ蜃ｦ逅・ｵ先棡繧定ｪｭ縺ｿ霎ｼ繧
        # ------------------
        logger.info("蜃ｦ逅・ｵ先棡隱ｭ縺ｿ霎ｼ縺ｿ繝・せ繝磯幕蟋・)
        
        # 繝・せ繝医′螳御ｺ・＠縺溘°繝√ぉ繝・け
        max_wait = 30  # 譛螟ｧ蠕・ｩ滓凾髢難ｼ育ｧ抵ｼ・
        start_time = time.time()
        test_completed = 0
        
        while test_completed == 0 and (time.time() - start_time) < max_wait:
            try:
                test_completed = pyff.get_data("test_completed")
                if test_completed == 0:
                    logger.info("FreeFEM縺ｮ蜃ｦ逅・′螳御ｺ・☆繧九・繧貞ｾ・▲縺ｦ縺・∪縺・..")
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"繝・せ繝亥ｮ御ｺ・ヵ繝ｩ繧ｰ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ荳ｭ縺ｫ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: {e}")
                time.sleep(1)
        
        if test_completed != 1:
            logger.error(f"FreeFEM縺ｮ蜃ｦ逅・′繧ｿ繧､繝繧｢繧ｦ繝医∪縺溘・繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆")
            return False
        
        # 蜃ｦ逅・ｵ先棡繧定ｪｭ縺ｿ霎ｼ繧
        result_int = pyff.get_data("result_int")
        logger.info(f"謨ｴ謨ｰ蛟､縺ｮ蜃ｦ逅・ｵ先棡: result_int = {result_int}")
        
        result_double = pyff.get_data("result_double")
        logger.info(f"豬ｮ蜍募ｰ乗焚轤ｹ蛟､縺ｮ蜃ｦ逅・ｵ先棡: result_double = {result_double}")
        
        result_string = pyff.get_data("result_string")
        logger.info(f"譁・ｭ怜・縺ｮ蜃ｦ逅・ｵ先棡: result_string = {result_string}")
        
        # 驟榊・縺ｮ蜃ｦ逅・ｵ先棡繧定ｪｭ縺ｿ霎ｼ繧
        result_array = pyff.get_data("result_array")
        logger.info(f"驟榊・縺ｮ蜃ｦ逅・ｵ先棡: result_array = {result_array}")
        
        # 邨先棡縺ｮ讀懆ｨｼ
        # ------------------
        logger.info("蜃ｦ逅・ｵ先棡縺ｮ讀懆ｨｼ髢句ｧ・)
        
        # 譛溷ｾ・＆繧後ｋ蛟､縺ｨ縺ｮ豈碑ｼ・
        expected_int = test_int + 10
        expected_double = test_double * 2.0
        expected_string = test_string + " [蜃ｦ逅・ｸ・"
        expected_array = test_array + 5.0
        
        success = True
        
        if result_int != expected_int:
            logger.error(f"謨ｴ謨ｰ蛟､縺ｮ讀懆ｨｼ繧ｨ繝ｩ繝ｼ: 譛溷ｾ・{expected_int}, 螳滄圀={result_int}")
            success = False
        
        if abs(result_double - expected_double) > 1e-10:
            logger.error(f"豬ｮ蜍募ｰ乗焚轤ｹ蛟､縺ｮ讀懆ｨｼ繧ｨ繝ｩ繝ｼ: 譛溷ｾ・{expected_double}, 螳滄圀={result_double}")
            success = False
        
        if result_string != expected_string:
            logger.error(f"譁・ｭ怜・縺ｮ讀懆ｨｼ繧ｨ繝ｩ繝ｼ: 譛溷ｾ・{expected_string}, 螳滄圀={result_string}")
            success = False
        
        if not np.allclose(result_array, expected_array):
            logger.error(f"驟榊・縺ｮ讀懆ｨｼ繧ｨ繝ｩ繝ｼ: 譛溷ｾ・{expected_array}, 螳滄圀={result_array}")
            success = False
        
        if success:
            logger.info("繝・せ繝育ｵ先棡: 謌仙粥 - 縺吶∋縺ｦ縺ｮ讀懆ｨｼ縺梧ｭ｣蟶ｸ縺ｫ螳御ｺ・＠縺ｾ縺励◆")
        else:
            logger.error("繝・せ繝育ｵ先棡: 螟ｱ謨・- 荳驛ｨ縺ｮ讀懆ｨｼ縺ｫ螟ｱ謨励＠縺ｾ縺励◆")
        
        # 邨先棡縺ｮ繧ｵ繝槭Μ繝ｼ繧偵ヵ繧｡繧､繝ｫ縺ｫ譖ｸ縺崎ｾｼ繧
        with open("test_pyfreefem_result.txt", "w", encoding="utf-8") as f:
            f.write("PyFreeFEM繝・せ繝育ｵ先棡繧ｵ繝槭Μ繝ｼ\n")
            f.write("======================\n\n")
            f.write(f"繝・せ繝育ｵ先棡: {'謌仙粥' if success else '螟ｱ謨・}\n\n")
            
            f.write("蜈･蜉帛､:\n")
            f.write(f"  謨ｴ謨ｰ蛟､: {test_int}\n")
            f.write(f"  豬ｮ蜍募ｰ乗焚轤ｹ蛟､: {test_double}\n")
            f.write(f"  譁・ｭ怜・: {test_string}\n")
            f.write(f"  驟榊・: {test_array}\n\n")
            
            f.write("蜃ｦ逅・ｵ先棡:\n")
            f.write(f"  謨ｴ謨ｰ蛟､: {result_int}\n")
            f.write(f"  豬ｮ蜍募ｰ乗焚轤ｹ蛟､: {result_double}\n")
            f.write(f"  譁・ｭ怜・: {result_string}\n")
            f.write(f"  驟榊・: {result_array}\n")
        
        # 繧ｯ繝ｪ繝ｼ繝ｳ繧｢繝・・
        pyff.cleanup()
        logger.info("繝ｪ繧ｽ繝ｼ繧ｹ繧偵け繝ｪ繝ｼ繝ｳ繧｢繝・・縺励∪縺励◆")
        
        return success
    
    except SharedMemoryError as e:
        logger.error(f"蜈ｱ譛峨Γ繝｢繝ｪ繧ｨ繝ｩ繝ｼ: {e}")
        return False
    except FreeFEMExecutionError as e:
        logger.error(f"FreeFEM螳溯｡後お繝ｩ繝ｼ: {e}")
        return False
    except DataTypeError as e:
        logger.error(f"繝・・繧ｿ蝙九お繝ｩ繝ｼ: {e}")
        return False
    except Exception as e:
        logger.error(f"莠域悄縺励↑縺・お繝ｩ繝ｼ: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        logger.info("PyFreeFEM繝・せ繝育ｵゆｺ・)

if __name__ == "__main__":
    success = test_pyfreefem()
    sys.exit(0 if success else 1) 
