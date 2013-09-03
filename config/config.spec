[jabber_account]
jid = string
password = string
resource = string

[management]
  command_prefix = string
  admins = string_list
  allowed_affiliations = string_list

[rooms]
   [[__many__]]
   jid = string
   nickname = string
   
[plugins]
  pool_workers = integer(min=0)
  [[__many__]]
    module = string
    
  [[chatlog]]
    [[[config]]]
      folder = string
      
  [[translator]]
    [[[config]]]
      max_tasks = integer(min=-1)
      translations = integer(min=0)
      reply_probability = float(0,1)