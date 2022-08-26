import json
from collections import Counter, defaultdict
from inspect import ArgInfo
from pathlib import Path
from typing import Dict, Union

import arabic_reshaper
from bidi.algorithm import get_display
from hazm import Normalizer, sent_tokenize, word_tokenize
from loguru import logger
from src.data import DATA_DIR
from wordcloud import WordCloud


class ChatStatistics:
    """Genreate chat statistics from a telegram chat json file
    """

    def __init__(self, chat_json: Union[str, Path]):
        """
        :param chat_json: path to telegram chat json file
        """
        # Load chat data
        logger.info(f"Loading chat data from {chat_json}")
        with open(chat_json) as f:
            self.chat_data = json.load(f)

        self.normalizer = Normalizer()

        #load stopwords
        logger.info(f"Loading stopwords from {DATA_DIR / 'stopwords.txt'}")
        stop_words = open(DATA_DIR / 'stop_words.txt').readlines()
        stop_words = map(str.strip, stop_words)
        self.stop_words = set(map(self.normalizer.normalize, stop_words))
    
    @staticmethod
    def rebuild_msg(sub_messages):
        msg_text = ''
        for sub_msg in sub_messages:
            if isinstance(sub_msg, str):
                msg_text += sub_msg
            elif 'text' in sub_msg:
                msg_text += sub_msg['text']
                
        return msg_text
    
    
    def msg_has_question(self, msg):
        '''check if a message has a question mark'''  
        if not isinstance(msg['text'], str):
            msg['text'] = self.rebuild_msg(msg['text'])
        
        sentences = sent_tokenize(msg['text'])
        for sentence in sentences:
            if ('?' not in sentence) and ('؟' not in sentence):
                continue
                
            return True

    
    def get_top_users(self, top_n: int = 10) -> Dict[str, int]:
        """Get top n users in chat
        :param top_n: number of top users to return, default is 10
        :return: dict of top users and their message count
        rtype: dict
        """
        #check messages for questions
        is_question = defaultdict(bool)
        for msg in self.chat_data['messages']:
            if not isinstance(msg['text'], str):
                msg['text'] = self.rebuild_msg(msg['text'])
            
            sentences = sent_tokenize(msg['text'])
            for sentence in sentences:
                if ('?' not in sentence) and ('؟' not in sentence):
                    continue
                    
                is_question[msg['id']] = True
                break
        
        logger.info("Generating top users statistics...")
        users = []
        for msg in self.chat_data['messages']:
            if not msg.get('reply_to_message_id'):
                continue
    
            if is_question[msg['reply_to_message_id']] is False:
                continue
            users.append(msg['from'])
            
        return dict(Counter(users).most_common(top_n))
    
    
    def generate_word_cloud(self, output_dir: Union[str, Path]):
        """Generate word cloud from chat data
        :param output_dir: path to output directory for word cloud image
        """

        logger.info("generating text from chat data...") 
        text_content = ''
        for msg in self.chat_data['messages']:
            if isinstance(msg['text'], str):
                tokens = word_tokenize(msg['text'])
                tokens = list(filter(lambda item: item not in self.stop_words, tokens))
                
                text_content += f"{' '.join(tokens)}"

        # normalize and reshape text for final word cloud
        text_content = self.normalizer.normalize(text_content)
        text_content = arabic_reshaper.reshape(text_content)
        text_content = get_display(text_content)

        logger.info(f"Generating word cloud ...")
        # generate word cloud
        wordcloud = WordCloud(
            font_path=str(DATA_DIR / '/BHoma.ttf'), background_color='white', 
            width= 800, height= 600, 
            margin=2, max_words=200, max_font_size=40,
            ).generate(text_content)

    
        logger.info(f"Saving word cloud to {output_dir}")
        wordcloud.to_file(str(Path(output_dir) / 'wordcloud.png'))



if __name__ == "__main__":
    chat_stats = ChatStatistics(chat_json=DATA_DIR / "ML.json")
    top_users = chat_stats.get_top_users(top_n=10)
    print(top_users)
    chat_stats.generate_word_cloud(output_dir=DATA_DIR)
    print('Done!')
