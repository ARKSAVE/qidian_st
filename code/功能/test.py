import json
import re

import post_url
post = post_url.Post("https://www.qidian.com/chapter/1043456425/828015189/")
soup = post.post_("https://www.qidian.com/chapter/1043456425/828015189/")
book_info = soup.find('script',type='application/json').get_text()
json_data = json.loads(book_info)
print(re.sub(r"<p>","\n",json_data['pageContext']['pageProps']['pageData']['chapterInfo']['content']))
